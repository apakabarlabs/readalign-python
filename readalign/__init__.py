from .aligner import align, pair
from .alignment import Equivalent
from .pieces import cuts, pauses
from .rules import rules
from .silence import energy_frames, held, speech_level, speech_threshold
from .weighting import EnglishSyllableWeighting, EvenWeighting, SpeechWeighting
from .words import RecognizedWord, WordMatch, WordSpan, fold, normalize, printed_parts

__version__ = "0.6.0"
__all__ = [
    "EnglishSyllableWeighting",
    "Equivalent",
    "EvenWeighting",
    "RecognizedWord",
    "SpeechWeighting",
    "WordMatch",
    "WordSpan",
    "align",
    "cuts",
    "energy_frames",
    "fold",
    "held",
    "normalize",
    "pair",
    "pauses",
    "printed_parts",
    "rules",
    "speech_level",
    "speech_threshold",
]
