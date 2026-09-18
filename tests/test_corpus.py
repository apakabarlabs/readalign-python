import itertools

import pytest

from readalign.aligner import align, fill, match, pair
from readalign.pieces import UnevenPiecesError, cuts, joined, pauses
from readalign.rules import rules
from readalign.silence import energy_frames, held, speech_level
from readalign.weighting import EnglishSyllableWeighting
from readalign.words import RecognizedWord, WordSpan, letters, normalize, printed_parts, similarity
from tests.corpus import (
    TOLERANCE,
    asserts_something,
    cases,
    check_span,
    check_well_formed,
    heard_words,
    load,
    patch_from,
    waveform_of,
    weighting_for,
)


def named(name: str) -> pytest.MarkDecorator:
    found = cases(name)
    return pytest.mark.parametrize("case", found, ids=[case["name"] for case in found])


@named("align_tests.yaml")
def test_aligns_as_the_corpus_says(case: dict) -> None:
    name = case["name"]
    assert asserts_something(case, "want", "want_empty", "strictly_increasing"), f"{name}: asserts nothing"

    spans = align(
        case["expected"],
        heard_words(case),
        case["duration"],
        weighting_for(case),
        patch_from(case),
    )

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
            assert abs(later.start - earlier.end) < TOLERANCE, f"{name}: words {index} and {index + 1} do not touch"


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
            assert later.start >= earlier.end - TOLERANCE, f"{name}: two words claim the same instant"


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

    marks = [WordSpan(mark["start"], mark["end"]) for mark in case["spans"]]

    spans = held(marks, waveform_of(case), case["sample_rate"], case.get("limit", rules().hold_limit))

    check_well_formed(spans, len(marks), name)
    for expectation in case.get("want", []):
        check_span(spans[expectation["word"]], expectation, name)


SPEECH_LEVEL_CASES = load("hold_tests.yaml")["speech_level"]


@pytest.mark.parametrize("case", SPEECH_LEVEL_CASES, ids=[case["name"] for case in SPEECH_LEVEL_CASES])
def test_measures_how_loudly_the_recording_speaks(case: dict) -> None:
    name = case["name"]
    assert asserts_something(case, "equals", "at_least"), f"{name}: pins nothing"

    level = speech_level(energy_frames(waveform_of(case), case["sample_rate"]))

    if "equals" in case:
        assert abs(level - case["equals"]) < TOLERANCE, f"{name}: {level}"
    if "at_least" in case:
        assert level >= case["at_least"], f"{name}: {level}"


def word_cases(section: str) -> pytest.MarkDecorator:
    found = load("word_tests.yaml")[section]
    return pytest.mark.parametrize("case", found, ids=[str(case) for case in found])


@word_cases("printed_parts")
def test_counts_printed_parts_as_the_corpus_says(case: dict) -> None:
    assert printed_parts(case["word"]) == case["parts"], case["word"]


@word_cases("letters")
def test_cuts_a_word_into_letters_as_the_corpus_says(case: dict) -> None:
    assert letters(case["word"]) == case["want"], case["word"]


@word_cases("normalize")
def test_normalizes_as_the_corpus_says(case: dict) -> None:
    assert normalize(case["word"]) == case["want"]


@word_cases("similarity")
def test_scores_likeness_as_the_corpus_says(case: dict) -> None:
    score = similarity(case["left"], case["right"])
    if "equals" in case:
        assert abs(score - case["equals"]) < TOLERANCE
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


PAUSE_CASES = load("piece_tests.yaml")["pauses"]
CUT_CASES = load("piece_tests.yaml")["cuts"]


@pytest.mark.parametrize("case", PAUSE_CASES, ids=[case["name"] for case in PAUSE_CASES])
def test_finds_the_pauses_the_corpus_names(case: dict) -> None:
    found = pauses(waveform_of(case), case["sample_rate"])

    assert found == case["equals"], f"{case['name']}: {found}"


@pytest.mark.parametrize("case", CUT_CASES, ids=[case["name"] for case in CUT_CASES])
def test_cuts_where_the_corpus_says(case: dict) -> None:
    pieces = cuts(waveform_of(case), case["sample_rate"])

    assert pieces == [tuple(piece) for piece in case["equals"]], f"{case['name']}: {pieces}"


@pytest.mark.parametrize("case", CUT_CASES, ids=[case["name"] for case in CUT_CASES])
def test_leaves_no_sample_out_of_every_piece(case: dict) -> None:
    samples = waveform_of(case)

    pieces = cuts(samples, case["sample_rate"])

    assert pieces[0][0] == 0, f"{case['name']}: starts at {pieces[0][0]}"
    assert pieces[-1][1] == len(samples), f"{case['name']}: ends short"
    for earlier, later in itertools.pairwise(pieces):
        # Overlap where a pause allows it, but never a gap: a sample no piece holds is a
        # word no recogniser is ever asked about.
        assert later[0] <= earlier[1], f"{case['name']}: a gap between pieces"
        assert later[0] > earlier[0], f"{case['name']}: a piece that goes nowhere"


JOIN_CASES = load("piece_tests.yaml")["joins"]
JOIN_REFUSALS = load("piece_tests.yaml")["join_refusals"]


def transcripts_of(case: dict) -> list[list[RecognizedWord]]:
    return [[RecognizedWord(word["text"], word["start"], word["end"]) for word in piece] for piece in case["heard"]]


def pieces_of(case: dict) -> list[tuple[int, int]]:
    return [tuple(piece) for piece in case["pieces"]]


@pytest.mark.parametrize("case", JOIN_CASES, ids=[case["name"] for case in JOIN_CASES])
def test_joins_the_pieces_into_the_reading_the_corpus_names(case: dict) -> None:
    reading = joined(transcripts_of(case), pieces_of(case), case["sample_rate"])

    assert reading == [RecognizedWord(word["text"], word["start"], word["end"]) for word in case["equals"]], (
        f"{case['name']}: {reading}"
    )


@pytest.mark.parametrize("case", JOIN_REFUSALS, ids=[case["name"] for case in JOIN_REFUSALS])
def test_refuses_a_piece_and_its_transcript_that_do_not_pair_off(case: dict) -> None:
    with pytest.raises(UnevenPiecesError):
        joined(transcripts_of(case), pieces_of(case), case["sample_rate"])
