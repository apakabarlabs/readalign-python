from importlib.metadata import version

import readalign


def test_distribution_and_module_report_the_same_version() -> None:
    assert version("readalign") == readalign.__version__
