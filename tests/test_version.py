import re
from importlib.metadata import version
from pathlib import Path

import readalign


def test_distribution_and_module_report_the_same_version() -> None:
    assert version("readalign") == readalign.__version__


def test_the_module_reports_the_version_the_changelog_releases_last() -> None:
    changelog = (Path(__file__).parent.parent / "CHANGELOG.md").read_text(encoding="utf-8")
    assert readalign.__version__ == re.search(r"^## (\d+\.\d+\.\d+)$", changelog, re.MULTILINE)[1]
