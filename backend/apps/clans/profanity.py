from pathlib import Path

from django.core.exceptions import ValidationError

_WORDS = None


def _load_words():
    global _WORDS
    if _WORDS is not None:
        return _WORDS
    path = Path(__file__).resolve().parent.parent / "lfg" / "profanity_words.txt"
    words = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            w = line.strip().lower()
            if w and not w.startswith("#"):
                words.add(w)
    _WORDS = words
    return _WORDS


def contains_profanity(text: str) -> bool:
    if not text:
        return False
    low = text.lower()
    for w in _load_words():
        if len(w) >= 3 and w in low:
            return True
    return False


def validate_no_profanity(value: str, field_label: str = "Текст"):
    if contains_profanity(value or ""):
        raise ValidationError(f"{field_label}: недопустимые слова")