from pathlib import Path

from setuptools import setup

setup(
    name="readalign",
    version="0.3.0",
    packages=["readalign"],
    package_data={"readalign": ["rules.yaml"]},
    install_requires=["PyYAML>=6.0.3", "regex>=2026.1.15"],
    python_requires=">=3.10",
    author="Apakabarlabs",
    description="Lines a speech recogniser's output up against the text that was read",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/apakabarlabs/readalign-python",
    project_urls={
        "Source": "https://github.com/apakabarlabs/readalign-python",
        "Changelog": "https://github.com/apakabarlabs/readalign-python/blob/main/CHANGELOG.md",
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Text Processing :: Linguistic",
    ],
)
