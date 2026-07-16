from django.core.exceptions import ValidationError


def validate_clan_name(value: str) -> None:
    value = value.strip()
    if len(value) < 3:
        raise ValidationError("Название клана должно быть не менее 3 символов")
    if len(value) > 100:
        raise ValidationError("Название клана должно быть не более 100 символов")

MAX_CLAN_PER_USER = 3