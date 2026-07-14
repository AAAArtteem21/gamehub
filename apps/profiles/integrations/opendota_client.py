import requests

class OpenDotaClient:
    BASE_URL = "https://api.opendota.com/api"

    def get_player(self,account_id):
        response = requests.get(f'{self.BASE_URL}/players/{account_id}',timeout=10)
        response.raise_for_status()
        return response.json()
    
    def get_recent_mathces(self,account_id):
        response = requests.get(f"{self.BASE_URL}/players/{account_id}/recentMatches",timeout=10)
        response.raise_for_status()
        return response.json()
    
    def get_win_loss(self,account_id):
        response = requests.get(f"{self.BASE_URL}/players/{account_id}/wl",timeout=10)
        response.raise_for_status()
        return response.json()
    