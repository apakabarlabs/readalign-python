[![Tests](https://github.com/apakabarlabs/readalign-python/actions/workflows/tests.yml/badge.svg)](https://github.com/apakabarlabs/readalign-python/actions/workflows/tests.yml)
# readalign-python

Lines a speech recogniser's output up against the text that was read, and says when each word of that text was spoken.

This is not transcription. The words are known in advance; the recogniser is only asked where they are, and it will get some of them wrong. So words are matched by how alike they look on paper rather than by equality, and a word left unmatched has its time interpolated from the words around it.

This is a Python port of [readalign-swift](https://github.com/apakabarlabs/readalign-swift). The tuned numbers and the cases both libraries are held to are synced from there with `make sync-yaml`, so the two cannot quietly drift apart.

## What it handles

- **A misheard word.** `stowage` comes back as `stoage`, `harbour` as `harbor`. Matched on similarity, so the word keeps its own time.
- **A mark the recogniser wrote without its diacritics.** `čaša` comes back as `casa`, `łódź` as `lodz`. Likeness is measured with the marks lifted, or a short word in a language that uses them would not be found at all.
- **A word boundary in the wrong place.** `shouldst owe` comes back as `should stow`: the same sound, the gap moved one consonant cluster. Matched as a pair, on a stricter bar than a single word.
- **One written word heard as several**, and **several written words heard as one**.
- **A word nobody said.** A gap costs less than a bad pair, so a false start or an `um` is passed over instead of being pushed into a neighbouring word.
- **A run of words the recogniser dropped.** Their time is shared across the gap they left, by speech weight.

## Use

```python
from readalign import RecognizedWord, align

spans = align(
    expected=["From", "fairest", "creatures", "we", "desire", "increase"],
    heard=[
        RecognizedWord("from", 0.00, 0.32),
        RecognizedWord("farest", 0.32, 0.81),
        RecognizedWord("creatures", 0.81, 1.44),
        RecognizedWord("we", 1.44, 1.60),
        RecognizedWord("desire", 1.60, 2.08),
        RecognizedWord("increase", 2.08, 2.72),
    ],
    duration=3.0,
)

assert spans[1].start == 0.32
assert spans[1].end == 0.81
```

One span per expected word, in seconds, in reading order. What a word is on the page — which line it sits in, which of its letters get painted — stays with the caller.

A recording nothing was heard in comes back empty rather than with a span per word, because every span would be a guess dressed as a measurement:

```python
from readalign import align

assert align(expected=["From", "fairest"], heard=[], duration=3.0) == []
```

Words go in **as they are printed**, hyphens and elision marks and all: the parts of a hyphenated compound are counted before the marks are taken off, and a compound heard as three words cannot be matched without that count.

To ask only which word came back as which, without times:

```python
from readalign import pair

matches = pair(
    expected=["hearts", "shouldst", "owe"],
    heard=["hearts", "should", "stow"],
    threshold=0.6,
)

# the pair whose boundary moved comes back as one match
assert any(m.expected == range(1, 3) and m.heard == range(1, 3) for m in matches)
```

### Recogniser patches

`pair` takes an optional `equivalent`, called as `(written, heard, the written word before it)`. It is for pairs a particular recogniser reliably gets wrong in a way likeness cannot carry, and it is asked with either side joined up as well.

```python
from readalign import pair

matches = pair(
    expected=["the", "heir"],
    heard=["the", "air"],
    threshold=0.6,
    equivalent=lambda written, heard, after: (written, heard) == ("heir", "air"),
)

assert any(m.expected == range(1, 2) for m in matches)
```

### Holding a word open through the silence after it

The one part that needs the recording. A recogniser marks where a word stops being audible, not where the voice has finished with it, so a passage played to the mark stops a hair short of itself. Give it the samples and the marks come back carried to the quiet:

```python
from readalign import WordSpan, held

samples = [0.5] * 1500 + [0.0] * 1000 + [0.5] * 2000 + [0.0] * 1000

spans = held([WordSpan(0.05, 0.10)], samples, sample_rate=10000)

assert spans[0].end > 0.10
```

### Other languages

Time is shared out among unmatched words by a weighting. `EnglishSyllableWeighting` counts vowel groups less a silent final `e`; `EvenWeighting` gives every word the same share, which is what a language it cannot count should use until someone writes one for it. Anything with a `weight(word)` method will do.

```python
from readalign import EvenWeighting, RecognizedWord, align

spans = align(
    expected=["kuća", "čaša", "šuma"],
    heard=[
        RecognizedWord("kuca", 0.0, 0.8),
        RecognizedWord("casa", 1.0, 1.8),
        RecognizedWord("suma", 2.0, 2.8),
    ],
    duration=4.0,
    weighting=EvenWeighting(),
)

assert spans[1].start == 1.0
```

## Install

```
pip install git+https://github.com/apakabarlabs/readalign-python@v0.2.0
```

Not on PyPI yet, so a consumer takes it from the tag.

The API at 0.2.0 is not settled and may change without a major version.

## Develop

```bash
make install
make test
make lint
make sync-yaml   # after the rules or the cases change in readalign-swift
```
