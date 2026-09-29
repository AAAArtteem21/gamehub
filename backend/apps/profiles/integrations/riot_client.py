import requests
from django.conf import settings
from urllib.parse import quote

class RiotError(Exception):
    pass


# platform → account/match routing region
PLATFORM_TO_REGION = {
    "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe",
    "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas",
    "kr": "asia", "jp1": "asia",
    "oc1": "sea",
}


class RiotClient:
    def __init__(self, platform: str = "euw1"):
        self.api_key = getattr(settings, "RIOT_API_KEY", "") or ""
        if not self.api_key:
            raise RiotError("RIOT_API_KEY не задан")
        self.platform = platform.lower()
        self.region = PLATFORM_TO_REGION.get(self.platform, "europe")

    def _headers(self):
        return {"X-Riot-Token": self.api_key}

    def _get(self, host, path, params=None):
        try:
            r = requests.get(
                f"https://{host}{path}",
                params=params or {},
                headers=self._headers(),
                timeout=20,
            )
            if r.status_code == 404:
                raise RiotError("Не найдено")
            if r.status_code == 401:
                raise RiotError("Riot API key неверный или просрочен")
            if r.status_code == 429:
                raise RiotError("Riot rate limit")
            r.raise_for_status()
            return r.json()
        except RiotError:
            raise
        except requests.RequestException as e:
            raise RiotError(f"Riot API: {e}") from e

    # --- Account (Riot ID → puuid) ---
    def get_account_by_riot_id(self, game_name: str, tag_line: str):
        gn = quote(game_name, safe="")
        tg = quote(tag_line, safe="")
        return self._get(
            f"{self.region}.api.riotgames.com",
            f"/riot/account/v1/accounts/by-riot-id/{gn}/{tg}",
        )
    def get_summoner_by_puuid(self, puuid: str):
        return self._get(
            f"{self.platform}.api.riotgames.com",
            f"/lol/summoner/v4/summoners/by-puuid/{puuid}",
        )

    def get_league_by_puuid(self, puuid: str):
        return self._get(
            f"{self.platform}.api.riotgames.com",
            f"/lol/league/v4/entries/by-puuid/{puuid}",
        )

    def get_match_ids(self, puuid: str, count: int = 15):
        return self._get(
            f"{self.region}.api.riotgames.com",
            f"/lol/match/v5/matches/by-puuid/{puuid}/ids",
            params={"start": 0, "count": count},
        )

    def get_match(self, match_id: str):
        return self._get(
            f"{self.region}.api.riotgames.com",
            f"/lol/match/v5/matches/{match_id}",
        )

    def get_challenger_league(self, queue: str = "RANKED_SOLO_5x5"):
        return self._get(
            f"{self.platform}.api.riotgames.com",
            f"/lol/league/v4/challengerleagues/by-queue/{queue}",
        )