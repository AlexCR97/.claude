#!/usr/bin/env python3
"""
The suite-wide exit-code vocabulary.

Every driver reads the same codes from every verb, so a skill can branch on an
exit code without knowing which source produced it.
"""

EXIT_OK = 0
EXIT_ERROR = 1
# `--require` unmet, or `drift` found the ticket moved.
EXIT_REQUIRE_UNMET = 2
EXIT_DRIFTED = 2
# An ambiguous bare reference, or a capability this source does not have.
EXIT_AMBIGUOUS = 3
EXIT_NO_CAPABILITY = 3
# The pre-`~/.tickets` layout is on disk and this ticket is not migrated yet.
EXIT_LEGACY_LAYOUT = 4
EXIT_NOT_FOUND = 5


class TicketError(Exception):
    """An error carrying the exit code the front door should exit with."""

    def __init__(self, message: str, code: int = EXIT_ERROR, hint: str = ""):
        super().__init__(message)
        self.message = message
        self.code = code
        self.hint = hint
