import requests
from django.conf import settings


class SteamClient:
    BASE_URL = "https://api.steampowered.com"

    def __init__(self):
        self.api_key = settings.STEAM_API_KEY

    def get_owned_games(self, steam_id: str):
        url = f"{self.BASE_URL}/IPlayerService/GetOwnedGames/v1/"
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "include_appinfo": True,
            "include_played_free_games": True,
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        return response.json().get("response", {}).get("games", [])

    def get_player_summary(self, steam_id):

        url = f"{self.BASE_URL}/ISteamUser/GetPlayerSummaries/v2/"

        params = {
            "key": self.api_key,
            "steamids": steam_id,
        }

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        players = response.json().get("response", {}).get("players", [])

        if players:
            return players[0]

        return None
    
    def get_cs2_stats(self, steam_id: str):
        url = f"{self.BASE_URL}/ISteamUserStats/GetUserStatsForGame/v2/"
        params = {"key": self.api_key, "steamid": steam_id, "appid": 730}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 400:
            return None
        response.raise_for_status()
        return response.json().get("playerstats", {}).get("stats", [])
    
    def get_player_summaries(self, steam_ids: list):
        url = f"{self.BASE_URL}/ISteamUser/GetPlayerSummaries/v2/"
        params = {"key": self.api_key, "steamids": ",".join(steam_ids)}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("response", {}).get("players", [])