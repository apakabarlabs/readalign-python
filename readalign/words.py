import unicodedata
from dataclasses import dataclass

import regex

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


def letters(word: str) -> list[str]:
    lowered = unicodedata.normalize("NFC", word).lower()
    return [cluster for cluster in regex.findall(r"\X", lowered) if is_letter(cluster)]


def normalize(word: str) -> str:
    return "".join(letters(word))


def printed_parts(word: str) -> int:
    return max(len([part for part in word.split("-") if part]), 1)


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
    written = regex.findall(r"\X", folded_left)
    said = regex.findall(r"\X", folded_right)
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
