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
    english_vowels: str
    folded_letters: dict[str, str]
    frame_seconds: float
    room_quantile: float
    speech_above_room: float
    quietest_room: float
    hold_limit: float


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
