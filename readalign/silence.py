import math
from collections.abc import Sequence

from .rules import rules
from .words import WordSpan


def energy_frames(samples: Sequence[float], sample_rate: float) -> list[float]:
    size = max(int(rules().frame_seconds * sample_rate), 1)
    frames = []
    for start in range(0, len(samples), size):
        window = samples[start : start + size]
        frames.append((sum(value * value for value in window) / len(window)) ** 0.5)
    return frames


def speech_threshold(frames: Sequence[float]) -> float:
    if not frames:
        return 0.0
    room = sorted(frames)[int(len(frames) * rules().room_quantile)]
    return max(
        room * rules().speech_above_room,
        rules().quietest_room,
        speech_level(frames) * rules().quiet_below_voice,
    )


def speech_level(frames: Sequence[float]) -> float:
    if not frames:
        return rules().quietest_speech
    quieter = int(len(frames) * (1 - rules().speech_from_loudest_share))
    louder = sorted(frames)[quieter:]
    return max(sum(louder) / len(louder), rules().quietest_speech)


def held(
    spans: list[WordSpan],
    samples: Sequence[float],
    sample_rate: float,
    limit: float | None = None,
) -> list[WordSpan]:
    frames = energy_frames(samples, sample_rate)
    if not frames:
        return spans

    limit = rules().hold_limit if limit is None else limit
    frame_seconds = rules().frame_seconds
    threshold = speech_threshold(frames)
    duration = len(samples) / sample_rate

    outcome = []
    for index, span in enumerate(spans):
        following = spans[index + 1].start if index + 1 < len(spans) else duration
        ceiling = min(following, span.end + limit)
        end = span.end
        frame = int(span.end / frame_seconds)
        went_quiet = False
        while (frame + 1) * frame_seconds <= ceiling and frame < len(frames):
            if frames[frame] < threshold:
                went_quiet = True
            elif went_quiet:
                break
            end = (frame + 1) * frame_seconds
            frame += 1
        outcome.append(WordSpan(span.start, min(max(span.end, end), max(following, span.start))))
    return outcome


def widened(
    spans: list[WordSpan],
    samples: Sequence[float],
    sample_rate: float,
    limit: float | None = None,
) -> list[WordSpan]:
    """Each word given the quiet on both sides of it, so that a cut along its edges keeps
    the consonants a recogniser leaves outside its mark.

    A start goes back from its mark through the word's own sound and then through the
    quiet before it, and stops where the recording speaks again; an end goes on the same
    way. Neither passes the middle of the gap to the neighbouring mark, the ends of the
    recording, or `limit` from its own mark. An edge that meets no quiet before one of
    those stays where it was: with no pause between two words there is nothing to give
    either of them. So does an edge that would move by less than `least_widening`, each
    edge judged on its own and the distance counted in samples.

    Where an edge between two words falls inside a sound, both words first meet in the
    middle of the nearest pause within `limit` of it: the recogniser marks a word from
    where it is sure of it, so the opening hiss of the next word, or the first stretch of
    a vowel it opens with, sounds before its mark. That holds for two words marked edge
    to edge and for two with a gap between their marks alike, since the gap can lie in
    the next word's own sound. The edge goes no further than the middle of either word,
    so a short word keeps the pause after it, and words whose marks overlap keep them.
    """
    frames = energy_frames(samples, sample_rate)
    if not frames:
        return spans

    limit = rules().hold_limit if limit is None else limit
    threshold = speech_threshold(frames)
    size = max(int(rules().frame_seconds * sample_rate), 1)
    each_frame = size / sample_rate
    duration = len(samples) / sample_rate
    spans = _settled(spans, frames, threshold, each_frame, limit, sample_rate)

    outcome = []
    for index, span in enumerate(spans):
        floor = max(0.0, span.start - limit)
        if index > 0:
            floor = max(floor, (spans[index - 1].end + span.start) / 2)
        ceiling = min(duration, span.end + limit)
        if index + 1 < len(spans):
            ceiling = min(ceiling, (span.end + spans[index + 1].start) / 2)

        start = span.start
        frame = (in_samples(span.start, sample_rate) + size - 1) // size - 1
        went_quiet = False
        while 0 <= frame < len(frames) and (frame + 1) * each_frame > floor:
            if frames[frame] < threshold:
                went_quiet = True
            elif went_quiet:
                break
            start = max(frame * each_frame, floor)
            frame -= 1

        end = span.end
        frame = in_samples(span.end, sample_rate) // size
        end_went_quiet = False
        while 0 <= frame < len(frames) and frame * each_frame < ceiling:
            if frames[frame] < threshold:
                end_went_quiet = True
            elif end_went_quiet:
                break
            end = min((frame + 1) * each_frame, ceiling)
            frame += 1

        least = in_samples(rules().least_widening, sample_rate)
        start_moves = in_samples(span.start - start, sample_rate) >= least
        end_moves = in_samples(end - span.end, sample_rate) >= least
        outcome.append(
            WordSpan(
                start if went_quiet and start_moves else span.start,
                end if end_went_quiet and end_moves else span.end,
            )
        )
    return outcome


def _settled(
    spans: list[WordSpan],
    frames: list[float],
    threshold: float,
    each_frame: float,
    limit: float,
    sample_rate: float,
) -> list[WordSpan]:
    pauses = _quiet_runs(frames, threshold, max(_half_up(rules().pause_seconds / each_frame), 1))
    settled = list(spans)
    for index in range(len(settled) - 1):
        word, following = settled[index], settled[index + 1]
        if in_samples(word.end, sample_rate) > in_samples(following.start, sample_rate):
            continue
        loud = [edge for edge in (following.start, word.end) if _in_sound(edge, frames, threshold, each_frame)]
        if not loud:
            continue
        lowest = (word.start + word.end) / 2
        highest = (following.start + following.end) / 2
        reachable = []
        for run_start, run_end in pauses:
            start, end = run_start * each_frame, run_end * each_frame
            distance = min(edge - end if end <= edge else start - edge for edge in loud)
            middle = (start + end) / 2
            if distance <= limit and lowest <= middle <= highest:
                reachable.append((distance, middle))
        if not reachable:
            continue
        middle = min(reachable)[1]
        settled[index] = WordSpan(word.start, middle)
        settled[index + 1] = WordSpan(middle, following.end)
    return settled


def _in_sound(at: float, frames: list[float], threshold: float, each_frame: float) -> bool:
    frame = _half_up(at / each_frame)
    return 0 < frame < len(frames) and frames[frame - 1] >= threshold and frames[frame] >= threshold


def _half_up(value: float) -> int:
    """Half a frame rounds up, as the Swift and Kotlin ports round it, not to even."""
    return math.floor(value + 0.5)


def _quiet_runs(frames: list[float], threshold: float, at_least: int) -> list[tuple[int, int]]:
    runs = []
    start = None
    for index, energy in enumerate(frames):
        if energy < threshold:
            if start is None:
                start = index
        elif start is not None:
            if index - start >= at_least:
                runs.append((start, index))
            start = None
    if start is not None and len(frames) - start >= at_least:
        runs.append((start, len(frames)))
    return runs


def in_samples(seconds: float, sample_rate: float) -> int:
    """Half a sample rounds up, as the Swift and Kotlin ports round it, not to even."""
    return math.floor(seconds * sample_rate + 0.5)
