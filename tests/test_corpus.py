import itertools

import pytest

from readalign.aligner import align, fill, match, pair
from readalign.rules import rules
from readalign.silence import held
from readalign.weighting import EnglishSyllableWeighting
from readalign.words import RecognizedWord, WordSpan, normalize, printed_parts, similarity
from tests.corpus import (
    asserts_something,
    cases,
    check_span,
    check_well_formed,
    heard_words,
    load,
    patch_from,
    weighting_for,
)


def named(name: str) -> pytest.MarkDecorator:
    found = cases(name)
    return pytest.mark.parametrize("case", found, ids=[case["name"] for case in found])


@named("align_tests.yaml")
def test_aligns_as_the_corpus_says(case: dict) -> None:
    name = case["name"]
    assert asserts_something(case, "want", "want_empty", "strictly_increasing"), f"{name}: asserts nothing"

    spans = align(case["expected"], heard_words(case), case["duration"], weighting_for(case))

    if case.get("want_empty"):
        assert spans == [], f"{name}: nothing rather than a guess"
        return

    check_well_formed(spans, len(case["expected"]), name)
    for expectation in case.get("want", []):
        check_span(spans[expectation["word"]], expectation, name)

    run = case.get("strictly_increasing")
    if run:
        for index in range(run[0], run[1] - 1):
            assert spans[index + 1].start > spans[index].start, (
                f"{name}: words {index} and {index + 1} land on one instant"
            )


@named("match_tests.yaml")
def test_places_words_as_the_corpus_says(case: dict) -> None:
    name = case["name"]
    assert asserts_something(case, "want", "contiguous"), f"{name}: asserts nothing"

    placed = match(case["expected"], heard_words(case), weighting_for(case))

    for expectation in case.get("want", []):
        word = placed.get(expectation["word"])
        assert word is not None, f"{name}: word {expectation['word']} was not placed at all"
        check_span(WordSpan(word.start, word.end), expectation, name)
        assert word.end > word.start, f"{name}: word {expectation['word']} has no length"

    run = case.get("contiguous")
    if run:
        for index in range(run[0], run[1] - 1):
            earlier, later = placed[index], placed[index + 1]
            assert abs(later.start - earlier.end) < 0.001, f"{name}: words {index} and {index + 1} do not touch"


@named("fill_tests.yaml")
def test_fills_as_the_corpus_says(case: dict) -> None:
    name = case["name"]
    assert asserts_something(case, "want", "non_overlapping"), f"{name}: asserts nothing"

    pairs = {found["word"]: RecognizedWord(found["text"], found["start"], found["end"]) for found in case["pairs"]}
    spans = fill(case["expected"], pairs, case["duration"], weighting_for(case))

    check_well_formed(spans, len(case["expected"]), name)
    for expectation in case.get("want", []):
        check_span(spans[expectation["word"]], expectation, name)

    if case.get("non_overlapping"):
        for earlier, later in itertools.pairwise(spans):
            assert later.start >= earlier.end - 0.001, f"{name}: two words claim the same instant"


@named("pair_tests.yaml")
def test_pairs_as_the_corpus_says(case: dict) -> None:
    name = case["name"]
    assert asserts_something(case, "want", "want_absent"), f"{name}: asserts nothing"

    matches = pair(case["expected"], case["heard"], case["threshold"], patch_from(case))

    def made(wanted: dict) -> bool:
        return any(
            found.expected == range(*wanted["expected"]) and found.heard == range(*wanted["heard"]) for found in matches
        )

    for wanted in case.get("want", []):
        assert made(wanted), f"{name}: no match with expected {wanted['expected']}, heard {wanted['heard']}"
    for unwanted in case.get("want_absent", []):
        assert not made(unwanted), (
            f"{name}: matched expected {unwanted['expected']}, heard {unwanted['heard']}, which hides two mistakes"
        )


@named("hold_tests.yaml")
def test_holds_as_the_corpus_says(case: dict) -> None:
    name = case["name"]
    assert asserts_something(case, "want"), f"{name}: asserts nothing"

    samples = [
        stretch["level"] for stretch in case["waveform"] for _ in range(round(stretch["seconds"] * case["sample_rate"]))
    ]
    marks = [WordSpan(mark["start"], mark["end"]) for mark in case["spans"]]

    spans = held(marks, samples, case["sample_rate"], case.get("limit", rules().hold_limit))

    check_well_formed(spans, len(marks), name)
    for expectation in case.get("want", []):
        check_span(spans[expectation["word"]], expectation, name)


def word_cases(section: str) -> pytest.MarkDecorator:
    found = load("word_tests.yaml")[section]
    return pytest.mark.parametrize("case", found, ids=[str(case) for case in found])


@word_cases("printed_parts")
def test_counts_printed_parts_as_the_corpus_says(case: dict) -> None:
    assert printed_parts(case["word"]) == case["parts"], case["word"]


@word_cases("normalize")
def test_normalizes_as_the_corpus_says(case: dict) -> None:
    assert normalize(case["word"]) == case["want"]


@word_cases("similarity")
def test_scores_likeness_as_the_corpus_says(case: dict) -> None:
    score = similarity(case["left"], case["right"])
    if "equals" in case:
        assert abs(score - case["equals"]) < 0.001
    if "at_least" in case:
        assert score >= case["at_least"]
    if "at_most" in case:
        assert score <= case["at_most"]


@word_cases("english_syllables")
def test_counts_english_syllables_as_the_corpus_says(case: dict) -> None:
    counted = EnglishSyllableWeighting().syllable_count(case["word"])
    if "count" in case:
        assert counted == case["count"], case["word"]
    if "at_least" in case:
        assert counted >= case["at_least"], case["word"]
