import re
from pathlib import Path

import pytest

BLOCKS = re.findall(
    r"```python\n(.*?)\n```",
    (Path(__file__).parent / "README.md").read_text(encoding="utf-8"),
    re.DOTALL,
)


@pytest.mark.parametrize("block", BLOCKS, ids=range(len(BLOCKS)))
def test_readme_example_runs(block):
    exec(block, {})
