# apps/profiles/integrations/pubg_client.py
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
        return r.json()["data"][0]

    def get_season_stats(self, account_id, season_id="division.bro.official.pc-2018-28"):
        r = requests.get(
            f"{self.BASE_URL}/players/{account_id}/seasons/{season_id}",
            headers=self.headers, timeout=10,
        )
        r.raise_for_status()
        return r.json()