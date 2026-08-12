import re
from django.core.exceptions import ValidationError


def validate_external_id(platform, external_id):
    external_id = external_id.strip()
    if platform == "steam":
        if not re.fullmatch(r"\d{17}", external_id):
            raise ValidationError("Steam ID должен быть 17-значным числом (SteamID64)")
    elif platform == "opendota":
        if not external_id.isdigit():
            raise ValidationError("OpenDota account_id должен быть числом")
    elif platform == "faceit":
        if len(external_id) < 3:
            raise ValidationError("Faceit player_id/nickname слишком короткий")
    elif platform == "lol":
        if "#" not in external_id:
            raise ValidationError("Укажи в формате Ник#TAG (Riot ID)")
    elif platform == "valorant":
        if "#" not in external_id:
            raise ValidationError("Укажи в формате Ник#TAG (Riot ID)")
    elif platform == "pubg":
        if len(external_id) < 3:
            raise ValidationError("Укажи корректный никнейм PUBG (Steam)")
    elif platform == "roblox":
        if len(external_id) < 3:
            raise ValidationError("Укажи корректный никнейм Roblox")