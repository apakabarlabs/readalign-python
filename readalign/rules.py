from dataclasses import dataclass
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
    return Rules(**yaml.safe_load(text))
