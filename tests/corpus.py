import itertools
from collections.abc import Callable
from pathlib import Path

import yaml

from readalign.weighting import EnglishSyllableWeighting, EvenWeighting, SpeechWeighting
from readalign.words import RecognizedWord, WordSpan

TOLERANCE = 0.001


class UnusableWeighting:
    def weight(self, _word: str) -> float:
        return float("nan")


WEIGHTINGS: dict[str, SpeechWeighting] = {
    "english": EnglishSyllableWeighting(),
    "even": EvenWeighting(),
    "unusable": UnusableWeighting(),
}


def load(name: str) -> dict:
    path = Path(__file__).parent / "cases" / name
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def cases(name: str) -> list[dict]:
    return [case for section in load(name)["tests"] for case in section["cases"]]


def weighting_for(case: dict) -> SpeechWeighting:
    return WEIGHTINGS[case.get("weighting", "english")]


def heard_words(case: dict) -> list[RecognizedWord]:
    return [RecognizedWord(word["text"], word["start"], word["end"]) for word in case["heard"]]


def asserts_something(case: dict, *keys: str) -> bool:
    return any(case.get(key) for key in keys)


PINS = ("start", "end", "start_at_least", "end_at_least", "end_at_most")


def check_span(span: WordSpan, expectation: dict, where: str) -> None:
    subject = f"{where}, word {expectation['word']}"
    assert any(pin in expectation for pin in PINS), f"{subject}: pins nothing, so a key here is misspelt"
    if "start" in expectation:
        assert abs(span.start - expectation["start"]) < TOLERANCE, f"{subject}: start is {span.start}"
    if "end" in expectation:
        assert abs(span.end - expectation["end"]) < TOLERANCE, f"{subject}: end is {span.end}"
    if "start_at_least" in expectation:
        assert span.start >= expectation["start_at_least"] - TOLERANCE, f"{subject}: start is {span.start}"
    if "end_at_least" in expectation:
        assert span.end >= expectation["end_at_least"] - TOLERANCE, f"{subject}: end is {span.end}"
    if "end_at_most" in expectation:
        assert span.end <= expectation["end_at_most"] + TOLERANCE, f"{subject}: end is {span.end}"


def check_well_formed(spans: list[WordSpan], count: int, where: str) -> None:
    assert len(spans) == count, f"{where}: one span per word"
    for index, span in enumerate(spans):
        assert span.end >= span.start, f"{where}: word {index} ends before it starts"
    for earlier, later in itertools.pairwise(spans):
        assert later.start >= earlier.start - TOLERANCE, f"{where}: spans go backwards"


def patch_from(case: dict) -> Callable[[str, str, str | None], bool] | None:
    entries = case.get("equivalent")
    if not entries:
        return None

    def vouched(written: str, said: str, after: str | None) -> bool:
        return any(
            entry["written"] == written
            and entry["heard"] == said
            and (entry.get("after") is None or entry["after"] == after)
            for entry in entries
        )

    return vouched
