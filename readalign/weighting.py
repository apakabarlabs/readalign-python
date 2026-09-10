from typing import Protocol

from .rules import rules


class SpeechWeighting(Protocol):
    def weight(self, word: str) -> float: ...


class EnglishSyllableWeighting:
    def weight(self, word: str) -> float:
        return float(self.syllable_count(word))

    def syllable_count(self, word: str) -> int:
        vowels = frozenset(rules().english_vowels)
        letters = "".join(character for character in word.lower() if character.isalpha())
        if not letters:
            return 1

        count = 0
        previous_was_vowel = False
        for letter in letters:
            is_vowel = letter in vowels
            if is_vowel and not previous_was_vowel:
                count += 1
            previous_was_vowel = is_vowel
        if len(letters) > 2 and letters.endswith("e") and not letters.endswith("le") and count > 1:
            count -= 1
        return max(count, 1)


class EvenWeighting:
    def weight(self, word: str) -> float:
        return 1.0
