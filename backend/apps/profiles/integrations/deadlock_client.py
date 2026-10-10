import time
import requests
from django.conf import settings


class DeadlockError(Exception):
    pass


class DeadlockRateLimited(DeadlockError):
    pass


class DeadlockClient:
    BASE_URL = "https://api.deadlock-api.com"
    MAX_RETRIES = 2

    def __init__(self):
        self.api_key = getattr(settings, "DEADLOCK_API_KEY", "") or ""
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if self.api_key:
            self.session.headers.update({"X-API-Key": self.api_key})

    def _get(self, path, params=None, timeout=15):
        url = f"{self.BASE_URL}{path}"
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                r = self.session.get(url, params=params or {}, timeout=timeout)
            except requests.Timeout:
                raise DeadlockError("Deadlock API не отвечает")
            except requests.RequestException as e:
                raise DeadlockError(f"Deadlock API: {e}")

            if r.status_code == 429:
                if attempt < self.MAX_RETRIES:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise DeadlockRateLimited("Deadlock API: лимит (IP)")
            if r.status_code == 404:
                raise DeadlockError("Не найдено")
            if r.status_code >= 500:
                raise DeadlockError("Deadlock API недоступен")
            r.raise_for_status()
            return r.json()
        raise DeadlockError("Deadlock API: ошибка")

    def get_match_metadata(self, match_id):
        return self._get(f"/v1/matches/{match_id}/metadata")

    def get_rank(self, account_id):
        return self._get(f"/v1/players/{account_id}/rank")

    def get_match_history(self, account_id, *, only_stored=True):
        """
        only_stored=True — больше матчей из БД API, без жёсткого IP-лимита.
        force_refetch — только вручную/редко: тянет Steam, лимит 1/час.
        """
        params = {}
        if only_stored:
            params["only_stored_history"] = "true"
        return self._get(f"/v1/players/{account_id}/match-history", params=params)

    def get_hero_stats(self, account_id):
        return self._get(f"/v1/players/{account_id}/hero-stats")

    def get_account_stats(self, account_id):
        return self._get(f"/v1/players/{account_id}/account-stats")

    def get_mate_stats(self, account_id):
        return self._get(f"/v1/players/{account_id}/mate-stats")

    def get_match_metadata(self, match_id):
        return self._get(f"/v1/matches/{match_id}/metadata")

    def get_heroes(self):
        return self._get("/v1/assets/heroes")

    def get_ranks(self):
        return self._get("/v1/assets/ranks")