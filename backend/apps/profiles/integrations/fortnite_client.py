import requests
from django.conf import settings


class FortniteClient:
    BASE_URL = "https://public-api.tracker.gg/v2/fortnite/standard"

    def __init__(self):
        self.headers = {"TRN-Api-Key": settings.TRN_API_KEY}

    def get_profile(self, epic_nickname):
        r = requests.get(f"{self.BASE_URL}/profile/epic/{epic_nickname}", headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()["data"]