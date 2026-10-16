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
    return max(room * rules().speech_above_room, rules().quietest_room)


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
    """
    frames = energy_frames(samples, sample_rate)
    if not frames:
        return spans

    limit = rules().hold_limit if limit is None else limit
    threshold = speech_threshold(frames)
    size = max(int(rules().frame_seconds * sample_rate), 1)
    each_frame = size / sample_rate
    duration = len(samples) / sample_rate

    outcome = []
    for index, span in enumerate(spans):
        floor = max(0.0, span.start - limit)
        if index > 0:
            floor = max(floor, (spans[index - 1].end + span.start) / 2)
        ceiling = min(duration, span.end + limit)
        if index + 1 < len(spans):
            ceiling = min(ceiling, (span.end + spans[index + 1].start) / 2)

        start = span.start
        frame = (round(span.start * sample_rate) + size - 1) // size - 1
        went_quiet = False
        while 0 <= frame < len(frames) and (frame + 1) * each_frame > floor:
            if frames[frame] < threshold:
                went_quiet = True
            elif went_quiet:
                break
            start = max(frame * each_frame, floor)
            frame -= 1

        end = span.end
        frame = round(span.end * sample_rate) // size
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


def in_samples(seconds: float, sample_rate: float) -> int:
    """Half a sample rounds up, as the Swift and Kotlin ports round it, not to even."""
    return math.floor(seconds * sample_rate + 0.5)
