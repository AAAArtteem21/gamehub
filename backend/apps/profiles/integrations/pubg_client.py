# apps/profiles/integrations/pubg_client.py
import requests
from django.conf import settings


class PubgError(Exception):
    pass


APP_ID = 578080  # PUBG


class PubgClient:
    """Лёгкий режим: часы из Steam. Полная BR-стата — только с official PUBG API."""

    def __init__(self):
        self.steam_key = getattr(settings, "STEAM_API_KEY", "") or ""
        if not self.steam_key:
            raise PubgError("STEAM_API_KEY не задан")

    def get_playtime_minutes(self, steam_id: str) -> int:
        url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        r = requests.get(
            url,
            params={
                "key": self.steam_key,
                "steamid": steam_id,
                "include_appinfo": 1,
                "include_played_free_games": 1,
            },
            timeout=15,
        )
        r.raise_for_status()
        games = r.json().get("response", {}).get("games") or []
        for g in games:
            if g.get("appid") == APP_ID:
                return int(g.get("playtime_forever") or 0)
        raise PubgError("PUBG не найден в библиотеке Steam (профиль закрыт или игры нет)")

    def get_player_summary(self, steam_id: str):
        url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
        r = requests.get(
            url,
            params={"key": self.steam_key, "steamids": steam_id},
            timeout=15,
        )
        r.raise_for_status()
        players = r.json().get("response", {}).get("players") or []
        return players[0] if players else {}