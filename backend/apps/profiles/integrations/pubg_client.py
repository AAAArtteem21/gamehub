
import requests
from django.conf import settings


class PubgClient:
    BASE_URL = "https://api.pubg.com/shards/steam"

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.PUBG_API_KEY}",
            "Accept": "application/vnd.api+json",
        }

    def get_player(self, player_name):
        r = requests.get(
            f"{self.BASE_URL}/players",
            params={"filter[playerNames]": player_name},
            headers=self.headers, timeout=10,
        )
        r.raise_for_status()
        data = r.json()["data"]
        if not data:
            raise ValueError("Игрок не найден в PUBG")
        return data[0]

    def get_season_stats(self, account_id, season_id):
        r = requests.get(
            f"{self.BASE_URL}/players/{account_id}/seasons/{season_id}",
            headers=self.headers, timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def get_current_season_id(self):
        r = requests.get(f"{self.BASE_URL}/seasons", headers=self.headers, timeout=10)
        r.raise_for_status()
        for season in r.json()["data"]:
            if season["attributes"]["isCurrentSeason"]:
                return season["id"]
        return None