from typing import Protocol

from .rules import rules
from .words import letters as letter_clusters


class SpeechWeighting(Protocol):
    def weight(self, word: str) -> float: ...


class EnglishSyllableWeighting:
    def weight(self, word: str) -> float:
        return float(self.syllable_count(word))

    def syllable_count(self, word: str) -> int:
        vowels = frozenset(rules().english_vowels)
        clusters = letter_clusters(word)
        if not clusters:
            return 1

        count = 0
        previous_was_vowel = False
        for cluster in clusters:
            is_vowel = cluster in vowels
            if is_vowel and not previous_was_vowel:
                count += 1
            previous_was_vowel = is_vowel
        spelled = "".join(clusters)
        if len(clusters) > 2 and spelled.endswith("e") and not spelled.endswith("le") and count > 1:
            count -= 1
        return max(count, 1)


class EvenWeighting:
    def weight(self, word: str) -> float:
        return 1.0
