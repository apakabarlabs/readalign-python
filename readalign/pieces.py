"""Cutting a recording into the pieces a recogniser is given one at a time.

Every side that listens to the same reading has to cut it the same way. A piece boundary
changes what comes back near it, and a runtime left to cut on its own cuts elsewhere: a
forty-second reading handed whole to one recogniser and in fifteen-second windows to
another is two different questions, and the answers cannot be held against each other. So
the cut is made here, by rule, before any of them is asked.
"""

from collections.abc import Callable, Sequence

from .rules import rules
from .silence import energy_frames, speech_threshold
from .words import RecognizedWord, normalize


class UnevenPiecesError(ValueError):
    def __init__(self, heard: int, pieces: int) -> None:
        super().__init__(f"{heard} transcripts for {pieces} pieces")


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
    """Cut the recording into the pieces it is asked in, each overlapping the one before.

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


def joined(
    heard: Sequence[Sequence[RecognizedWord]],
    pieces: Sequence[tuple[int, int]],
    sample_rate: float,
) -> list[RecognizedWord]:
    """One reading out of what each piece came back with.

    The pieces overlap, so the words at a seam arrive twice, and the second copy is
    dropped by time and text together: the same word marked within `same_moment` of one
    already kept is one word. Placed where it falls in the whole recording, so a caller
    hands over what it was given piece by piece and gets the reading back.

    A piece the recogniser had nothing to say about is an answer, not a failure: a
    stretch of silence is transcribed as no words at all. A count of transcripts that
    does not match the count of pieces is a failure, and is refused rather than quietly
    paired off until the shorter of the two runs out.
    """
    if len(heard) != len(pieces):
        raise UnevenPiecesError(len(heard), len(pieces))
    reading: list[RecognizedWord] = []
    for words, (start, _end) in zip(heard, pieces, strict=True):
        offset = start / sample_rate
        for word in words:
            placed = RecognizedWord(
                text=word.text,
                start=word.start + offset,
                end=word.end + offset,
            )
            if not any(_same_word(kept, placed) for kept in reading):
                reading.append(placed)
    return reading


def heard(
    piece: Sequence[float],
    sample_rate: float,
    asking: Callable[[Sequence[float]], Sequence[RecognizedWord]],
) -> list[RecognizedWord]:
    """Ask the recogniser for one piece, and again with less of its tail while nothing comes.

    Parakeet answers some pieces of ordinary speech with no words at all, and whether it
    does turns on where the piece starts and how long it is together: the mel statistics
    are taken over the piece, so its length moves them, and past some edge the decoder
    predicts blank at every frame. Handing over a little less of the tail moves the piece
    off that edge. Nothing here tells speech from silence, so a piece that is genuinely
    silent pays for the whole list before answering nothing, which is why a piece shorter
    than `shortest_worth_asking_again` is not asked again at all.

    An answer won this way is missing whatever was said in the tail that was cut off. Each
    piece the recording is cut into overlaps the next, and that overlap is what covers it.
    """
    words = list(asking(piece))
    if words or len(piece) / sample_rate < rules().shortest_worth_asking_again:
        return words
    for trim in rules().ask_again_trims:
        shorter = len(piece) - int(trim * sample_rate)
        if shorter <= 0:
            break
        again = list(asking(piece[:shorter]))
        if again:
            return again
    return words


def _same_word(kept: RecognizedWord, word: RecognizedWord) -> bool:
    return abs(kept.start - word.start) < rules().same_moment and normalize(kept.text) == normalize(word.text)
