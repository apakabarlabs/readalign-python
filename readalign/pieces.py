"""Cutting a recording into the pieces a recogniser is given one at a time.

Every side that listens to the same reading has to cut it the same way. A piece boundary
changes what comes back near it, and a runtime left to cut on its own cuts elsewhere: a
forty-second reading handed whole to one recogniser and in fifteen-second windows to
another is two different questions, and the answers cannot be held against each other. So
the cut is made here, by rule, before any of them is asked.
"""

from collections.abc import Sequence

from .rules import rules
from .silence import energy_frames, speech_threshold


def pauses(samples: Sequence[float], sample_rate: float) -> list[int]:
    """Where the recording is quiet long enough that a cut there takes no word in half.

    The middle of each stretch of quiet, in samples. A stop inside a word is quiet too,
    which is why a pause has a length to reach before it counts as one.
    """
    frames = energy_frames(samples, sample_rate)
    if not frames:
        return []
    threshold = speech_threshold(frames)
    # Quiet is only quiet between speech. Where nothing stands above the threshold there
    # is no voice to pause, and the whole recording would otherwise read as one long
    # pause and offer its own middle as a place to cut.
    if not any(frame >= threshold for frame in frames):
        return []

    each_frame = rules().frame_seconds
    quiet_enough = max(int(rules().pause_seconds / each_frame), 1)
    found = []
    quiet = 0
    for index, energy in enumerate(frames):
        if energy < threshold:
            quiet += 1
            continue
        if quiet >= quiet_enough:
            found.append(int((index - quiet // 2) * each_frame * sample_rate))
        quiet = 0
    if quiet >= quiet_enough:
        found.append(int((len(frames) - quiet // 2) * each_frame * sample_rate))
    return found


def cuts(samples: Sequence[float], sample_rate: float) -> list[tuple[int, int]]:
    """The pieces the recording is asked in, in samples, each overlapping the one before.

    A piece ends at the last pause that leaves it long enough to carry a line and short
    enough for the runtime to take whole; where no pause falls there, it ends on length
    alone, because a piece that grows to find a pause is the very window this avoids. The
    next piece begins one pause earlier than the last ended, so every word is heard whole
    by at least one of them.
    """
    longest = int(rules().piece_seconds * sample_rate)
    if len(samples) <= longest or longest <= 0:
        return [(0, len(samples))]
    shortest = int(rules().piece_seconds * rules().shortest_piece_share * sample_rate)
    marks = pauses(samples, sample_rate)

    pieces = []
    start = 0
    while len(samples) - start > longest:
        within = [mark for mark in marks if start + shortest < mark < start + longest]
        cut = within[-1] if within else start + longest
        pieces.append((start, cut))
        # One pause back, but never back past half a piece: the overlap is there to carry
        # the words at the seam, and a pause near the start of this piece would hand the
        # next one almost the same range, over and over.
        back = [mark for mark in marks if start + shortest <= mark < cut]
        start = back[-1] if back else cut
    pieces.append((start, len(samples)))
    return pieces
