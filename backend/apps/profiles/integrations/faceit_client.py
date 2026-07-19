import requests
from django.conf import settings 


import requests
from django.conf import settings


class FaceitClient:
    BASE_URL = "https://open.faceit.com/data/v4"

    def __init__(self):
        self.headers = {"Authorization": f"Bearer {settings.FACEIT_API_KEY}"}

    def get_player_by_nickname(self, nickname):
        r = requests.get(f"{self.BASE_URL}/players", params={"nickname": nickname}, headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_player_stats(self, player_id, game="cs2"):
        r = requests.get(f"{self.BASE_URL}/players/{player_id}/stats/{game}", headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_recent_matches(self, player_id, game="cs2", limit=20):
        r = requests.get(
            f"{self.BASE_URL}/players/{player_id}/history",
            params={"game": game, "limit": limit},
            headers=self.headers, timeout=10,
        )
        r.raise_for_status()
        return r.json()