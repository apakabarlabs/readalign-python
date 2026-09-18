import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from .rules import rules


@dataclass(frozen=True)
class RecognizedWord:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class WordSpan:
    start: float
    end: float


@dataclass(frozen=True)
class WordMatch:
    expected: range
    heard: range


def is_letter(cluster: str) -> bool:
    return cluster[0].isalpha() or unicodedata.category(cluster[0]) == "Nl"


MARKS = frozenset({"Mn", "Me", "Mc"})
ZERO_WIDTH_NON_JOINER = "\u200c"
ZERO_WIDTH_JOINER = "\u200d"


def joins_on(character: str, last: str) -> bool:
    """Whether this belongs to the letter being read rather than starting the next one."""
    if unicodedata.category(character) in MARKS or character in (ZERO_WIDTH_NON_JOINER, ZERO_WIDTH_JOINER):
        return True
    return rules().joins(last) and character.isalpha()


def clusters(word: str) -> list[str]:
    """Cut a word into the pieces a reader sees as one character each.

    Cut by the rules this library shares rather than by whatever the platform carries,
    because every platform carries a different answer and a different vintage of it: one
    cuts a zero-width joiner away from the word it joins, another breaks a joined pair of
    consonants in two. Sharing the rules is what keeps the ports reading one word.
    """
    found: list[str] = []
    letter = ""
    for character in word:
        if letter and not joins_on(character, letter[-1]):
            found.append(letter)
            letter = ""
        letter += character
    if letter:
        found.append(letter)
    return found


def letters(word: str) -> list[str]:
    lowered = unicodedata.normalize("NFC", word).lower()
    return [cluster for cluster in clusters(lowered) if is_letter(cluster)]


def normalize(word: str) -> str:
    return "".join(letters(word))


def printed_parts(word: str) -> int:
    return max(len([part for part in word.split("-") if part]), 1)


#: A token carrying one of these opens a word; they are part of no word.
OPENS_A_WORD = frozenset("▁| \t\n")

#: What the recogniser could not spell at all, which belongs in no word.
UNHEARD = "<unk>"


def spoken(tokens: Sequence[RecognizedWord]) -> list[RecognizedWord]:
    """Gather a recogniser's tokens into the words they spell.

    A recogniser answers in tokens, not in words: `be`, `aut`, `y's`. Where one word ends
    and the next begins is the recogniser's convention, not the caller's, and every side
    that reads the same model has to read that convention the same way -- otherwise one
    returns `beauty's` where another returns `beautys` and a third splits the word in two,
    and the three cannot be held against each other however alike they heard the sound.

    Each word is timed from the token it opens with to the one it closes with. Marks at
    either end of a word are left off: a word the model wrote `increase,` is the word
    `increase`, and the comma is the model's punctuation rather than anything it heard.
    Marks inside a word stay, because `beauty's` and `self-substantial` are words and
    `beautys` is not.
    """
    words: list[RecognizedWord] = []
    text = ""
    start = 0.0
    end = 0.0
    for token in tokens:
        for character in token.text.replace(UNHEARD, ""):
            if character in OPENS_A_WORD:
                if text:
                    words.append(RecognizedWord(text=text, start=start, end=end))
                    text = ""
                continue
            if not text:
                start = token.start
            text += character
            end = token.end
    if text:
        words.append(RecognizedWord(text=text, start=start, end=end))
    return [trimmed for trimmed in (_trimmed(word) for word in words) if trimmed is not None]


def _trimmed(word: RecognizedWord) -> RecognizedWord | None:
    text = word.text
    while text and not text[0].isalnum():
        text = text[1:]
    while text and not text[-1].isalnum():
        text = text[:-1]
    return RecognizedWord(text=text, start=word.start, end=word.end) if text else None


def fold(word: str) -> str:
    kept = [character for character in unicodedata.normalize("NFD", word) if not rules().lifts(character)]
    lifted = unicodedata.normalize("NFC", "".join(kept))
    listed = rules().folded_letters
    return "".join(listed.get(character, character) for character in lifted)


def similarity(left: str, right: str) -> float:
    folded_left, folded_right = fold(left), fold(right)
    if folded_left == folded_right:
        return 1.0
    if not folded_left or not folded_right:
        return 0.0
    written = clusters(folded_left)
    said = clusters(folded_right)
    return 1 - edit_distance(written, said) / max(len(written), len(said))


def edit_distance(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for row, left_character in enumerate(left, start=1):
        current = [row]
        for column, right_character in enumerate(right, start=1):
            current.append(
                min(
                    current[column - 1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]
