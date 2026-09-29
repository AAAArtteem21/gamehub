import requests
from django.conf import settings


class FortniteError(Exception):
    pass


class FortniteClient:
    BASE = "https://fortnite-api.com/v2"

    def __init__(self):
        self.api_key = getattr(settings, "FORTNITE_API_KEY", "") or ""
        if not self.api_key:
            raise FortniteError("FORTNITE_API_KEY не задан")

    def _headers(self):
        return {"Authorization": self.api_key}

    def get_br_stats(self, name: str, time_window: str = "lifetime"):
        """
        time_window: 'lifetime' | 'season'
        """
        try:
            r = requests.get(
                f"{self.BASE}/stats/br/v2",
                params={
                    "name": name,
                    "accountType": "epic",
                    "timeWindow": time_window,
                },
                headers=self._headers(),
                timeout=25,
            )
            if r.status_code == 404:
                raise FortniteError("Игрок Fortnite не найден")
            if r.status_code == 401:
                raise FortniteError("Fortnite API key неверный")
            if r.status_code == 403:
                raise FortniteError("Статистика скрыта в настройках Epic")
            r.raise_for_status()
            body = r.json()
            if body.get("status") != 200:
                raise FortniteError(body.get("error") or "Fortnite API error")
            return body.get("data") or {}
        except FortniteError:
            raise
        except requests.RequestException as e:
            raise FortniteError(f"Fortnite API: {e}") from e