"""The exit-code vocabulary every verb shares, so a skill can branch on a code without parsing text."""

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_AMBIGUOUS = 3


class SdlcError(Exception):
    def __init__(self, message: str, code: int = EXIT_ERROR, hint: str = ""):
        super().__init__(message)
        self.message = message
        self.code = code
        self.hint = hint
