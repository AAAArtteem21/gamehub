import requests
from django.conf import settings


class ValorantClient:
    BASE_URL = "https://api.henrikdev.xyz/valorant"

    def __init__(self):
        self.headers = {"Authorization": settings.VALORANT_API_KEY}

    def get_account(self, name, tag):
        r = requests.get(f"{self.BASE_URL}/v1/account/{name}/{tag}", headers=self.headers, timeout=10)
        r.raise_for_status()
        data = r.json().get("data")
        if not data:
            raise ValueError(f"Игрок {name}#{tag} не найден в Valorant")
        return data

    def get_mmr(self, name, tag, region="eu"):
        r = requests.get(f"{self.BASE_URL}/v2/mmr/{region}/{name}/{tag}", headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json().get("data") or {}

    def get_matches(self, name, tag, region="eu", size=25):
        r = requests.get(
            f"{self.BASE_URL}/v3/matches/{region}/{name}/{tag}",
            headers=self.headers, params={"size": size}, timeout=10,
        )
        r.raise_for_status()
        return r.json().get("data") or []

    def get_match_details(self, match_id):
        r = requests.get(f"{self.BASE_URL}/v2/match/{match_id}", headers=self.headers, timeout=10)
        r.raise_for_status()
        data = r.json().get("data")
        if not data:
            raise ValueError("Матч не найден")
        return data

    def get_leaderboard(self, region="eu", size=15):
        r = requests.get(
            f"{self.BASE_URL}/v3/leaderboard/{region}",
            headers=self.headers, params={"size": size}, timeout=10,
        )
        r.raise_for_status()
        data = r.json().get("data") or {}
        # HenrikDev иногда отдаёт список сразу, иногда в .players
        if isinstance(data, list):
            return data[:size]
        return data.get("players", []) or []