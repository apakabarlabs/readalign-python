"""Cutting a recording into the pieces a recogniser is given one at a time.

Every side that listens to the same reading has to cut it the same way. A piece boundary
changes what comes back near it, and a runtime left to cut on its own cuts elsewhere: a
forty-second reading handed whole to one recogniser and in fifteen-second windows to
another is two different questions, and the answers cannot be held against each other. So
the cut is made here, by rule, before any of them is asked.
"""

from collections.abc import Callable, Sequence
from itertools import dropwhile, takewhile
from typing import NamedTuple

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
    by at least one of them. Where that would leave no overlap, the next piece begins by
    `edge_overlap` instead. This is confined to empty seams: a floor that moved every
    shorter overlap was measured worse.
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
        start = back[-1] if back else max(start, cut - int(rules().edge_overlap * sample_rate))
    pieces.append((start, len(samples)))
    return pieces


def joined(
    heard: Sequence[Sequence[RecognizedWord]],
    pieces: Sequence[tuple[int, int]],
    sample_rate: float,
) -> list[RecognizedWord]:
    """One reading out of what each piece came back with.

    The pieces overlap, so the words at a seam arrive twice, and the second copy is
    dropped by the text: the longest run the two pieces say alike inside the overlap is
    found, everything the coming piece says up to the end of it comes off, and so does
    whatever the piece before said past it. Placed where it falls in the whole recording,
    so a caller hands over what it was given piece by piece and gets the reading back.

    By the text and not by the clock, because the clock is the one thing two builds of one
    model do not share: the same word decoded in two pieces comes back a fifth of a second
    apart on one runtime and differently again on the next, so a rule that asks how close
    two marks are decides differently on each of them. The words agree where the marks do
    not.

    A piece the recogniser had nothing to say about is an answer, not a failure: a
    stretch of silence is transcribed as no words at all. A count of transcripts that
    does not match the count of pieces is a failure, and is refused rather than quietly
    paired off until the shorter of the two runs out.
    """
    if len(heard) != len(pieces):
        raise UnevenPiecesError(len(heard), len(pieces))
    reading: list[RecognizedWord] = []
    covered_to = 0.0
    for words, (start, end) in zip(heard, pieces, strict=True):
        offset = start / sample_rate
        placed = [RecognizedWord(text=word.text, start=word.start + offset, end=word.end + offset) for word in words]
        seam = _agreement(reading, placed, offset, covered_to)
        if seam.kept_after_it:
            del reading[len(reading) - seam.kept_after_it :]
        reading += placed[seam.coming_up_to_it :]
        covered_to = end / sample_rate
    return reading


def _agreement(
    kept: Sequence[RecognizedWord],
    coming: Sequence[RecognizedWord],
    overlap_from: float,
    covered_to: float,
) -> "_Seam":
    """Find the longest run the two pieces say alike in the ground they both cover.

    Answers how many words come off the end of the reading so far and how many off the
    front of the coming piece.

    Only words inside that ground can be a second copy, so the search is held to it: a
    word the reading genuinely says twice, further along, is out of reach and stays.

    The run is looked for anywhere inside the overlap rather than at its edges, because a
    recogniser drops or invents a word at the edge of what it was given -- one piece ended
    "...by time decease we" where the other heard no "we" -- and a run pinned to the edges
    would find nothing and leave the whole overlap said twice. A run of one word is taken
    only when it is the whole of what the coming piece says in the overlap, or a word as
    common as "the" would pair with itself by chance.

    Past the run the coming piece is believed and the piece before it is not: they cover
    the same seconds there, and the one that goes on past them heard them with what
    follows while the other was hearing the last of what it was given.
    """
    tail = [normalize(word.text) for word in dropwhile(lambda word: word.start < overlap_from, kept)]
    head = [normalize(word.text) for word in takewhile(lambda word: word.start < covered_to, coming)]
    if not tail or not head:
        return _Seam(0, 0)

    longest = 0
    ends_in_tail = 0
    ends_in_head = 0
    for first in range(len(tail)):
        for second in range(len(head)):
            run = 0
            while first + run < len(tail) and second + run < len(head) and tail[first + run] == head[second + run]:
                run += 1
            if run > longest:
                longest = run
                ends_in_tail = first + run
                ends_in_head = second + run
    if longest > 1 or longest == len(head):
        return _Seam(len(tail) - ends_in_tail, ends_in_head)
    return _Seam(0, 0)


class _Seam(NamedTuple):
    kept_after_it: int
    coming_up_to_it: int


def heard(
    piece: Sequence[float],
    sample_rate: float,
    asking: Callable[[Sequence[float]], Sequence[RecognizedWord]],
) -> list[RecognizedWord]:
    """Ask for one piece, recovering an empty or prematurely stopped answer.

    Parakeet answers some pieces of ordinary speech with no words at all, and whether it
    does turns on where the piece starts and how long it is together: the mel statistics
    are taken over the piece, so its length moves them, and past some edge the decoder
    predicts blank at every frame. Handing over a little less of the tail moves the piece
    off that edge. Nothing here tells speech from silence, so a piece that is genuinely
    silent pays for the whole list before answering nothing, which is why a piece shorter
    than `shortest_worth_asking_again` is not asked again at all.

    A non-empty answer can also stop before speech resumes later in its audio. That tail
    is asked again with already recognised context and accepted only when the two answers
    share enough words to join without a duplicate.

    An empty answer won by trimming is missing whatever was said in the tail that was cut
    off. Each piece overlaps the next, and that overlap is what covers it.
    """
    words = list(asking(piece))
    if words:
        return _recovered_tail(words, piece, sample_rate, asking)
    if len(piece) / sample_rate < rules().shortest_worth_asking_again:
        return words
    for trim in rules().ask_again_trims:
        shorter = len(piece) - int(trim * sample_rate)
        if shorter <= 0:
            break
        again = list(asking(piece[:shorter]))
        if again:
            return again
    return words


def _recovered_tail(
    words: list[RecognizedWord],
    piece: Sequence[float],
    sample_rate: float,
    asking: Callable[[Sequence[float]], Sequence[RecognizedWord]],
) -> list[RecognizedWord]:
    frames = energy_frames(piece, sample_rate)
    threshold = speech_threshold(frames)
    first_frame = int(words[-1].end / rules().frame_seconds)
    went_quiet = False
    for energy in frames[first_frame:]:
        if energy < threshold:
            went_quiet = True
        elif went_quiet:
            break
    else:
        return words

    overlap_from = max(0.0, words[-1].start - rules().partial_answer_overlap)
    start = int(overlap_from * sample_rate)
    offset = start / sample_rate
    coming = [RecognizedWord(word.text, word.start + offset, word.end + offset) for word in asking(piece[start:])]
    seam = _agreement(words, coming, offset, len(piece) / sample_rate)
    kept_after = seam.kept_after_it
    coming_up_to = seam.coming_up_to_it
    if not coming_up_to and coming and normalize(words[-1].text) == normalize(coming[0].text):
        coming_up_to = 1
    if not coming_up_to:
        return words
    kept = words[:-kept_after] if kept_after else words
    return [*kept, *coming[coming_up_to:]]
