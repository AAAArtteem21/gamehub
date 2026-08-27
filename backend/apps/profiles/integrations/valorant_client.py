import requests
from django.conf import settings


class ValorantClient:
    BASE_URL = "https://api.henrikdev.xyz/valorant"

    def __init__(self):
        self.headers = {"Authorization": settings.VALORANT_API_KEY}

    def get_account(self, name, tag):
        r = requests.get(f"{self.BASE_URL}/v1/account/{name}/{tag}", headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()["data"]

    def get_mmr(self, name, tag, region="eu"):
        r = requests.get(f"{self.BASE_URL}/v2/mmr/{region}/{name}/{tag}", headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()["data"]

    def get_matches(self, name, tag, region="eu", size=10):
        r = requests.get(
            f"{self.BASE_URL}/v3/matches/{region}/{name}/{tag}",
            headers=self.headers, params={"size": size}, timeout=10,
        )
        r.raise_for_status()
        return r.json()["data"]

    def get_mmr_history(self, name, tag, region="eu"):
        r = requests.get(f"{self.BASE_URL}/v1/mmr-history/{region}/{name}/{tag}", headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()["data"]

    def get_match_details(self, match_id, region="eu"):
        r = requests.get(f"{self.BASE_URL}/v2/match/{match_id}", headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()["data"]
