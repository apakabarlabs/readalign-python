from .alignment import Alignment, Equivalent
from .rules import rules
from .weighting import EnglishSyllableWeighting, SpeechWeighting
from .words import RecognizedWord, WordMatch, WordSpan


def pair(
    expected: list[str],
    heard: list[str],
    threshold: float,
    equivalent: Equivalent | None = None,
) -> list[WordMatch]:
    if not expected or not heard:
        return []
    alignment = Alignment(expected, heard, threshold, equivalent)
    return alignment.matches(alignment.scores())


def align(
    expected: list[str],
    heard: list[RecognizedWord],
    duration: float,
    weighting: SpeechWeighting | None = None,
) -> list[WordSpan]:
    if not expected or not heard:
        return []
    weighting = weighting or EnglishSyllableWeighting()
    return fill(expected, match(expected, heard, weighting), duration, weighting)


def match(
    expected: list[str],
    heard: list[RecognizedWord],
    weighting: SpeechWeighting | None = None,
) -> dict[int, RecognizedWord]:
    weighting = weighting or EnglishSyllableWeighting()
    placed: dict[int, RecognizedWord] = {}
    for found in pair(expected, [word.text for word in heard], rules().match_threshold):
        start = heard[found.heard.start].start
        end = heard[found.heard.stop - 1].end
        said = heard[found.heard.start].text
        if len(found.expected) == 1:
            placed[found.expected.start] = RecognizedWord(said, start, end)
            continue
        weights = [speech_weight(expected[index], weighting) for index in found.expected]
        total = sum(weights)
        cursor = start
        for index, weight in zip(found.expected, weights, strict=True):
            length = (end - start) * weight / total
            placed[index] = RecognizedWord(said, cursor, cursor + length)
            cursor += length
    return placed


def fill(
    expected: list[str],
    pairs: dict[int, RecognizedWord],
    duration: float,
    weighting: SpeechWeighting | None = None,
) -> list[WordSpan]:
    weighting = weighting or EnglishSyllableWeighting()
    spans: list[WordSpan | None] = [None] * len(expected)
    for index, word in pairs.items():
        spans[index] = WordSpan(word.start, word.end)

    index = 0
    while index < len(spans):
        if spans[index] is not None:
            index += 1
            continue

        run_end = index
        while run_end < len(spans) and spans[run_end] is None:
            run_end += 1

        first, last = index, run_end
        before = spans[index - 1] if index > 0 else None
        after = spans[run_end] if run_end < len(spans) else None
        run_start = before.end if before else 0.0
        run_finish = after.start if after else duration

        if run_finish - run_start < rules().room_enough * (run_end - index):
            host = swallower(range(index, run_end), spans, expected, weighting)
            stretch = spans[host] if host is not None else None
            if stretch is not None and host is not None:
                if host < index:
                    first, run_start = host, stretch.start
                else:
                    last, run_finish = host + 1, stretch.end

        weights = [speech_weight(expected[offset], weighting) for offset in range(first, last)]
        total = sum(weights)
        cursor = run_start
        for offset, weight in zip(range(first, last), weights, strict=True):
            length = max(run_finish - run_start, 0.0) * weight / total
            spans[offset] = WordSpan(cursor, cursor + length)
            cursor += length
        index = run_end
    return [span for span in spans if span is not None]


def swallower(
    run: range,
    spans: list[WordSpan | None],
    expected: list[str],
    weighting: SpeechWeighting,
) -> int | None:
    def per_syllable(index: int) -> float | None:
        if not 0 <= index < len(spans):
            return None
        span = spans[index]
        if span is None:
            return None
        return (span.end - span.start) / speech_weight(expected[index], weighting)

    before = per_syllable(run.start - 1)
    after = per_syllable(run.stop)
    if before is not None and after is not None:
        return run.stop if after >= before else run.start - 1
    if before is not None:
        return run.start - 1
    if after is not None:
        return run.stop
    return None


def speech_weight(word: str, weighting: SpeechWeighting) -> float:
    weight = weighting.weight(word)
    if weight != weight or weight in (float("inf"), float("-inf")):
        return 1.0
    return max(weight, 1.0)
