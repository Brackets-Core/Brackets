#!/usr/bin/env python3
"""Setup para Brackets - Sistema de Gestión de Bitácoras y Notas."""

from pathlib import Path
from setuptools import setup, find_packages


def read_version() -> str:
    metadata = {}
    version_file = Path(__file__).parent / "version.py"
    exec(version_file.read_text(encoding="utf-8"), metadata)
    return str(metadata["VERSION"])

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="brackets",
    version=read_version(),
    author="CodeAndRes",
    description="Sistema modular de gestión de bitácoras semanales y notas organizadas",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/CodeAndRes/Brackets",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Office/Business :: Scheduling",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "brackets=brackets.main:main",
        ],
    },
)
