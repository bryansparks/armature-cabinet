"""Errors raised for expected authoring mistakes (not bugs in this package)."""
from __future__ import annotations


class CabinetError(Exception):
    """A cabinet agent folder is missing, unreadable, or malformed.

    Raised at load time so the CLI can print a clean message instead of a
    traceback. Distinct from logical validation problems, which are returned
    (not raised) by ``validate_package``.
    """