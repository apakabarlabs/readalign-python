from dataclasses import dataclass, fields
from functools import lru_cache
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Rules:
    match_threshold: float
    join_floor: float
    gap_penalty: float
    mismatch_penalty: float
    room_enough: float
    join_span: int
    english_vowels: str
    silent_ending: str
    silent_ending_except_after: str
    shortest_with_a_silent_ending: int
    lightest_word: float
    lifted_marks_from: str
    lifted_marks_to: str
    letter_joiners: list[str]
    folded_letters: dict[str, str]
    frame_seconds: float
    room_quantile: float
    speech_above_room: float
    quietest_room: float
    hold_limit: float
    speech_from_loudest_share: float
    quietest_speech: float
    piece_seconds: float
    shortest_piece_share: float
    pause_seconds: float
    same_moment: float
    ask_again_trims: list[float]
    shortest_worth_asking_again: float

    def joins(self, character: str) -> bool:
        """Whether this mark writes one consonant joined to the next, making them one letter."""
        return any(int(code, 16) == ord(character) for code in self.letter_joiners)

    def lifts(self, character: str) -> bool:
        return int(self.lifted_marks_from, 16) <= ord(character) <= int(self.lifted_marks_to, 16)


@lru_cache(maxsize=1)
def rules() -> Rules:
    text = (Path(__file__).parent / "rules.yaml").read_text(encoding="utf-8")
    return read(yaml.safe_load(text))


class RulesIncompleteError(ValueError):
    def __init__(self, names: list[str]) -> None:
        super().__init__("rules.yaml is missing " + ", ".join(names))


class RuleNotANumberError(ValueError):
    def __init__(self, name: str, value: object) -> None:
        super().__init__(f"rules.yaml: {name} is not a number: {value!r}")


def read(written: dict) -> Rules:
    wanted = {field.name: field.type for field in fields(Rules)}
    missing = sorted(set(wanted) - set(written))
    if missing:
        raise RulesIncompleteError(missing)
    return Rules(**{name: as_declared(written[name], kind, name) for name, kind in wanted.items()})


def as_declared(value: object, kind: object, name: str) -> object:
    if kind is not float:
        return value
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as wrong:
        raise RuleNotANumberError(name, value) from wrong
