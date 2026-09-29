import requests
from django.conf import settings


class FaceitError(Exception):
    pass


class FaceitClient:
    BASE = "https://open.faceit.com/data/v4"

    def __init__(self):
        self.api_key = getattr(settings, "FACEIT_API_KEY", "") or ""
        if not self.api_key or self.api_key in ("222", "changeme"):
            raise FaceitError("FACEIT_API_KEY не задан или заглушка")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        })

    def _get(self, path, params=None, timeout=15):
        url = f"{self.BASE}{path}"
        r = self.session.get(url, params=params or {}, timeout=timeout)
        if r.status_code == 401:
            raise FaceitError("Faceit API key неверный")
        if r.status_code == 404:
            raise FaceitError("Не найдено")
        if r.status_code == 429:
            raise FaceitError("Faceit rate limit — подожди")
        r.raise_for_status()
        return r.json()

    def get_player_by_nickname(self, nickname: str):
        nickname = (nickname or "").strip()
        if not nickname:
            raise FaceitError("Укажи ник Faceit")
        return self._get("/players", params={"nickname": nickname})

    def get_player(self, player_id: str):
        return self._get(f"/players/{player_id}")

    def get_player_stats(self, player_id: str, game_id: str = "cs2"):
        """Lifetime stats + map segments"""
        return self._get(f"/players/{player_id}/stats/{game_id}")

    def get_history(self, player_id: str, game: str = "cs2", limit: int = 20, offset: int = 0):
        """Match list (ids, results, teams)"""
        return self._get(
            f"/players/{player_id}/history",
            params={"game": game, "offset": offset, "limit": min(limit, 100)},
        )

    def get_match(self, match_id: str):
        return self._get(f"/matches/{match_id}")

    def get_match_stats(self, match_id: str):
        return self._get(f"/matches/{match_id}/stats")

    def get_recent_match_stats(self, player_id: str, game_id: str = "cs2", limit: int = 20):
        """Per-match stats for last N games"""
        return self._get(
            f"/players/{player_id}/games/{game_id}/stats",
            params={"limit": min(limit, 20), "offset": 0},
        )