from pathlib import Path

import pytest

HERE = Path(__file__).parent
ORIGIN = HERE.parent.parent / "readalign-swift"

COPIES = [
    (HERE.parent / "readalign" / "rules.yaml", ORIGIN / "Sources/ReadAlign/Resources/rules.yaml"),
    *[
        (case, ORIGIN / "Tests/ReadAlignTests/Resources" / case.name)
        for case in sorted((HERE / "cases").glob("*.yaml"))
    ],
]


@pytest.mark.skipif(not ORIGIN.is_dir(), reason="the library this one is a port of is not checked out beside it")
@pytest.mark.parametrize(("copy", "origin"), COPIES, ids=[copy.name for copy, _ in COPIES])
def test_the_shared_file_is_the_one_it_was_copied_from(copy: Path, origin: Path) -> None:
    assert origin.is_file(), f"{origin.name} is gone from the library this one is a port of"
    assert copy.read_text(encoding="utf-8") == origin.read_text(encoding="utf-8"), (
        f"{copy.name} is not what it was copied from; run `make sync-yaml`"
    )


def test_every_shared_file_is_accounted_for() -> None:
    if not ORIGIN.is_dir():
        pytest.skip("the library this one is a port of is not checked out beside it")
    there = {path.name for path in (ORIGIN / "Tests/ReadAlignTests/Resources").glob("*.yaml")}
    here = {path.name for path in (HERE / "cases").glob("*.yaml")}
    assert there == here, f"cases only over there: {sorted(there - here)}; only here: {sorted(here - there)}"
