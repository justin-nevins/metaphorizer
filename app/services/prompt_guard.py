import re

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"you\s+are\s+now",
    r"system\s*:",
    r"<\s*/?system\s*>",
    r"</?(user|assistant|human|ai)\s*>",
    r"INST\]",
    r"\[INST\]",
    r"<<SYS>>",
]

_compiled = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def sanitize(text: str) -> str:
    result = text
    for pattern in _compiled:
        result = pattern.sub("[REDACTED]", result)
    return result.strip()


def sanitize_book_text(text: str) -> str:
    return sanitize(text)


def sanitize_user_input(text: str) -> str:
    return sanitize(text)
