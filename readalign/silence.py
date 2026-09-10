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
