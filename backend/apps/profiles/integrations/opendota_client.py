import requests
from django.core.cache import cache


class OpenDotaError(Exception):
    """Ошибка / недоступность OpenDota."""
    pass


class OpenDotaClient:
    BASE_URL = "https://api.opendota.com/api"
    TIMEOUT = 25  # было 10 — часто не успевало

    def _get(self, path, params=None):
        try:
            r = requests.get(
                f"{self.BASE_URL}{path}",
                params=params or {},
                timeout=self.TIMEOUT,
            )
            r.raise_for_status()
            return r.json()
        except requests.Timeout as e:
            raise OpenDotaError("OpenDota не отвечает (timeout). Попробуй позже.") from e
        except requests.RequestException as e:
            raise OpenDotaError(f"OpenDota ошибка: {e}") from e

    def get_player(self, account_id: str):
        return self._get(f"/players/{account_id}")

    def get_win_loss(self, account_id: str):
        return self._get(f"/players/{account_id}/wl")

    def get_recent_matches(self, account_id: str, limit: int = 20):
        return self._get(f"/players/{account_id}/matches", params={"limit": limit})

    def get_heroes(self, account_id: str):
        return self._get(f"/players/{account_id}/heroes")

    def get_hero_names(self):
        cached = cache.get("opendota_hero_names")
        if cached is not None:
            return cached
        data = self._get("/heroes")
        names = {h["id"]: h["localized_name"] for h in data}
        cache.set("opendota_hero_names", names, timeout=60 * 60 * 24)
        return names

    def get_match_details(self, match_id):
        return self._get(f"/matches/{match_id}")

    def get_pro_players(self):
        cached = cache.get("opendota_pro_players")
        if cached is not None:
            return cached
        data = self._get("/proPlayers")
        cache.set("opendota_pro_players", data, timeout=60 * 60)
        return data

    def get_item_names(self):
        cached = cache.get("opendota_item_names")
        if cached is not None:
            return cached
        data = self._get("/constants/items")
        result = {}
        for key, v in data.items():
            if isinstance(v, dict) and v.get("id") is not None:
                img_path = v.get("img", "")
                result[v["id"]] = {
                    "key": key,
                    "name": v.get("dname", key),
                    "icon_url": (
                        f"https://cdn.cloudflare.steamstatic.com{img_path}"
                        if img_path
                        else None
                    ),
                }
        cache.set("opendota_item_names", result, timeout=60 * 60 * 24)
        return result