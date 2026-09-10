from .aligner import align, pair
from .silence import held
from .weighting import EnglishSyllableWeighting, EvenWeighting, SpeechWeighting
from .words import RecognizedWord, WordMatch, WordSpan, normalize

__version__ = "0.2.0"
__all__ = [
    "EnglishSyllableWeighting",
    "EvenWeighting",
    "RecognizedWord",
    "SpeechWeighting",
    "WordMatch",
    "WordSpan",
    "align",
    "held",
    "normalize",
    "pair",
]
