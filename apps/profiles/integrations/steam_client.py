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
    
    #alooo