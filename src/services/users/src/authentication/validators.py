import re

USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_-]{5,25}")
USERNAME_ERROR = "Username must be 5-25 characters: letters, digits, _ or -"


def validate_username(name) -> str | None:
    """Return an error message, or None when `name` is an acceptable username."""
    if not isinstance(name, str) or not USERNAME_PATTERN.fullmatch(name):
        return USERNAME_ERROR
    return None
