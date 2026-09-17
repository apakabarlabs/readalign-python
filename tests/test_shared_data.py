"""The rules and the cases belong to the leading port and live here as a copy.

Nobody reads that repository at run time, so a copy left behind would keep this port on
older behaviour with every test still green: the case that never arrived is a case these
tests do not know. So the copies are held against the leading repository itself.
"""

from pathlib import Path
from urllib.request import urlopen

import pytest

HERE = Path(__file__).parent
ORIGIN = "https://raw.githubusercontent.com/apakabarlabs/readalign-swift/main/"
TIMEOUT = 10

# Every file copied from the leading port, as where it lives there and where it lives
# here. A new shared file is checked from the moment it is added to this list, rather
# than when somebody remembers to write a test for it.
SHARED = [
    ("Sources/ReadAlign/Resources/rules.yaml", HERE.parent / "readalign" / "rules.yaml"),
    *[
        (f"Tests/ReadAlignTests/Resources/{name}", HERE / "cases" / name)
        for name in (
            "align_tests.yaml",
            "fill_tests.yaml",
            "hold_tests.yaml",
            "match_tests.yaml",
            "pair_tests.yaml",
            "piece_tests.yaml",
            "word_tests.yaml",
        )
    ],
]


@pytest.mark.parametrize(("there", "here"), SHARED, ids=[here.name for _, here in SHARED])
def test_the_shared_file_is_the_one_it_was_copied_from(there: str, here: Path) -> None:
    with urlopen(ORIGIN + there, timeout=TIMEOUT) as answer:  # noqa: S310
        origin = answer.read().decode("utf-8")
    stale = f"{here.name} differs from the leading port; run `make sync-yaml`"
    assert here.read_text(encoding="utf-8") == origin, stale


def test_every_case_file_here_is_one_of_the_shared_ones() -> None:
    listed = {here.name for _, here in SHARED}
    found = {path.name for path in (HERE / "cases").glob("*.yaml")}
    assert found <= listed, f"case files nothing checks: {sorted(found - listed)}"
