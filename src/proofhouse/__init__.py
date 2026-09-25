"""Proofhouse prompt-operations framework."""

from importlib.metadata import PackageNotFoundError, version

try:
    # One source of truth: the installed distribution's version (pyproject.toml).
    __version__ = version("proofhouse")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "0+unknown"
