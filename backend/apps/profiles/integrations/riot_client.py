# apps/profiles/integrations/riot_client.py
import requests
from django.conf import settings


class RiotClient:
    REGION_ACCOUNT = "europe"  # americas / asia / europe — для account-v1
    REGION_LOL = "eun1"  # eun1/euw1/na1/kr — конкретный игровой сервер

    def __init__(self):
        self.headers = {"X-Riot-Token": settings.RIOT_API_KEY}

    def get_account_by_riot_id(self, game_name, tag_line):
        url = f"https://{self.REGION_ACCOUNT}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        r = requests.get(url, headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_summoner_by_puuid(self, puuid, region=None):
        region = region or self.REGION_LOL
        url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        r = requests.get(url, headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_ranked_stats(self, summoner_id, region=None):
        region = region or self.REGION_LOL
        url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
        r = requests.get(url, headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_match_history(self, puuid, count=10):
        url = f"https://{self.REGION_ACCOUNT}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        r = requests.get(url, headers=self.headers, params={"count": count}, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_match_details(self, match_id):
        url = f"https://{self.REGION_ACCOUNT}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        r = requests.get(url, headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_challenger_league(self, region="euw1"):
        url = f"https://{region}.api.riotgames.com/lol/league/v4/challengerleagues/by-queue/RANKED_SOLO_5x5"
        r = requests.get(url, headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_match_timeline(self, match_id):
        url = f"https://{self.REGION_ACCOUNT}.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
        r = requests.get(url, headers=self.headers, timeout=10)
        r.raise_for_status()
        return r.json()