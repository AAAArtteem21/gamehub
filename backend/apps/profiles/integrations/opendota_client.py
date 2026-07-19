import requests

class OpenDotaClient:
    BASE_URL = "https://api.opendota.com/api"

    def get_player(self, account_id: str):
        r = requests.get(f"{self.BASE_URL}/players/{account_id}", timeout=10)
        r.raise_for_status()
        return r.json()

    def get_win_loss(self, account_id: str):
        r = requests.get(f"{self.BASE_URL}/players/{account_id}/wl", timeout=10)
        r.raise_for_status()
        return r.json()

    def get_recent_matches(self, account_id: str, limit: int = 20):
        r = requests.get(f"{self.BASE_URL}/players/{account_id}/matches", params={"limit": limit}, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_heroes(self, account_id: str):
        
        r = requests.get(f"{self.BASE_URL}/players/{account_id}/heroes", timeout=10)
        r.raise_for_status()
        return r.json()

    def get_hero_names(self):
       
        r = requests.get(f"{self.BASE_URL}/heroes", timeout=10)
        r.raise_for_status()
        return {h["id"]: h["localized_name"] for h in r.json()}