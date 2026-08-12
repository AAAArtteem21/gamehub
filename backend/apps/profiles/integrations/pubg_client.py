import requests
from django.conf import settings


class PubgClient:
    """Через TRN (tracker.gg developers) — тот же провайдер, что и Fortnite"""
    BASE_URL = "https://public-api.tracker.gg/v2/pubg/standard"

    def __init__(self):
        self.headers = {"TRN-Api-Key": settings.TRN_API_KEY}

    def get_profile(self, platform, player_name):
        r = requests.get(
            f"{self.BASE_URL}/profile/{platform}/{player_name}",
            headers=self.headers, timeout=10,
        )
        r.raise_for_status()
        return r.json()["data"]