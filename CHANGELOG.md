# Changelog

## 0.3.0

Nothing you call has to change. What comes back changes wherever accents are involved, on either side — see Fixed.

### Added
- `align` takes the optional `equivalent` that `pair` already had: a function called with the written word, the heard word, and the written word before it — `None` at the start of the text — answering `True` when those two are the same word however unlike they are spelled. Left out, nothing is vouched for and likeness alone decides, as before. Homophones are why it now reaches the times and not only the pairing: read aloud, `queue` comes back written `cue` and `rustle` comes back `Russell`, and without a word for it the written word is passed over and its time shared out among its neighbours.

### Fixed
- Deciding whether two spellings are the same word ignores the accents of the Latin alphabet and nothing else. It used to ignore every combining mark Unicode knows, which reached far past the alphabet that was meant for: `мой` matched `мои`, and Japanese and Devanagari words differing only by a mark matched each other. Those no longer match, and the times such words were given move. Letters carrying a stroke rather than an accent, `ł` and `đ` among them, are folded to their plain letter as before.
- Two spellings are compared by the letters a reader sees rather than by the characters Unicode stores: `é` written as one character and `é` written as `e` followed by an accent now count as one letter apiece, where they used to differ twice over. A pair that used to fall short of `threshold`, the bar for being the same word, can now clear it — in Latin text as much as anywhere else.

## 0.2.0

First release of this library in Python. Nothing to migrate from.

It answers the same question, and to the same cases, as the Swift library it was written from: the two read one set of tuned numbers and one set of cases, so they cannot quietly come to disagree. The version starts at 0.2.0 rather than 0.1.0 because those numbers and cases are shared, and a shared change moves both libraries to the same version in the same release.

### Added

Three calls, for the case where you already hold the text that was read aloud.

- `align` takes the words of that text, the words a speech recogniser returned with the start and end it heard each at, and the length of the recording. It returns one start and one end per word of your text, in seconds, in reading order. A recording nothing was heard in returns nothing rather than a span per word.
- `pair` answers the same question without times: which written word came back as which heard word. Its `threshold` is how alike two words must be to count as the same word; its optional `equivalent` lets you vouch for a pair a particular recogniser always gets wrong, such as `heir` heard as `air`.
- `held` is the one call that needs the recording. A recogniser marks where a word stops being audible, not where the voice has finished with it, so a passage played to the mark stops a hair short of itself; this carries each mark into the quiet behind it, and never into the word that follows.

Plus `EnglishSyllableWeighting` and `EvenWeighting`, which decide how the recording is shared out among words the recogniser did not return at all, so that a long word does not get the same slice of a pause as `a`.

The alignment tolerates what recognisers do to a text they were not given: a misspelt word keeps its own time, a word written without its diacritics is still the word, a word boundary put in the wrong place is matched across both words at once, a hyphenated compound heard as three words is timed across all three, two written words heard as one share the stretch between them, and a word nobody said is passed over instead of being pushed onto a written word.
