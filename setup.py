from setuptools import find_packages, setup

setup(
    name="readalign",
    version="0.2.0",
    packages=find_packages(),
    install_requires=["PyYAML>=6.0"],
    python_requires=">=3.10",
    author="Apakabarlabs",
    description="Lines a speech recogniser's output up against the text that was read",
    package_data={"readalign": ["rules.yaml", "cases/*.yaml"]},
)
