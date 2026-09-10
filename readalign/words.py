import unicodedata
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


def normalize(word: str) -> str:
    return "".join(character for character in word.lower() if character.isalpha())


def printed_parts(word: str) -> int:
    return max(len(word.split("-")), 1)


def fold(word: str) -> str:
    lifted = "".join(
        character for character in unicodedata.normalize("NFD", word) if not unicodedata.combining(character)
    )
    listed = rules().folded_letters
    return "".join(listed.get(character, character) for character in lifted)


def similarity(left: str, right: str) -> float:
    left, right = fold(left), fold(right)
    if left == right:
        return 1.0
    if not left or not right:
        return 0.0
    return 1 - edit_distance(left, right) / max(len(left), len(right))


def edit_distance(left: str, right: str) -> int:
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
