from typing import Protocol

from .rules import rules
from .words import letters as letter_clusters


class SpeechWeighting(Protocol):
    def weight(self, word: str) -> float: ...


class EnglishSyllableWeighting:
    def weight(self, word: str) -> float:
        return float(self.syllable_count(word))

    def syllable_count(self, word: str) -> int:
        lightest = int(rules().lightest_word)
        vowels = frozenset(rules().english_vowels)
        clusters = letter_clusters(word)
        if not clusters:
            return lightest

        count = 0
        previous_was_vowel = False
        for cluster in clusters:
            is_vowel = cluster in vowels
            if is_vowel and not previous_was_vowel:
                count += 1
            previous_was_vowel = is_vowel
        if self.ends_silently(clusters) and count > 1:
            count -= 1
        return max(count, lightest)

    def ends_silently(self, clusters: list[str]) -> bool:
        if len(clusters) < rules().shortest_with_a_silent_ending:
            return False
        spelled = "".join(clusters)
        return spelled.endswith(rules().silent_ending) and not spelled.endswith(rules().silent_ending_except_after)


class EvenWeighting:
    def weight(self, _word: str) -> float:
        return 1.0
