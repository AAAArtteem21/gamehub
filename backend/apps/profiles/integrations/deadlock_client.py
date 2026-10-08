import time
import requests
from django.conf import settings


class DeadlockError(Exception):
    pass


class DeadlockRateLimited(DeadlockError):
    pass


class DeadlockClient:
    """
    api.deadlock-api.com. Ключ ОПЦИОНАЛЕН (DEADLOCK_API_KEY в .env):
    без ключа работаем в IP-лимитах (~20 req/min на rank-бакет).
    Retry только на 429 с backoff. 404 = игрок не найден (не роняем синк).
    """
    BASE_URL = "https://api.deadlock-api.com"
    MAX_RETRIES = 2

    def __init__(self):
        self.api_key = getattr(settings, "DEADLOCK_API_KEY", "") or ""
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if self.api_key:
            self.session.headers.update({"X-API-Key": self.api_key})

    def _get(self, path, params=None, timeout=12):
        url = f"{self.BASE_URL}{path}"
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                r = self.session.get(url, params=params or {}, timeout=timeout)
            except requests.Timeout:
                raise DeadlockError("Deadlock API не отвечает, попробуй позже")
            except requests.RequestException as e:
                raise DeadlockError(f"Deadlock API: сетевая ошибка ({e})")

            if r.status_code == 429:
                if attempt < self.MAX_RETRIES:
                    time.sleep(2 * (attempt + 1))  # backoff: 2s, 4s
                    continue
                raise DeadlockRateLimited("Deadlock API: лимит запросов (IP)")
            if r.status_code == 404:
                raise DeadlockError("Игрок не найден в Deadlock")
            if r.status_code >= 500:
                raise DeadlockError("Deadlock API временно недоступен")
            r.raise_for_status()
            return r.json()
        raise DeadlockError("Deadlock API: неизвестная ошибка")

    # --- Players ---
    def get_rank(self, account_id):
        return self._get(f"/v1/players/{account_id}/rank")

    def get_match_history(self, account_id):
        return self._get(f"/v1/players/{account_id}/match-history")

    def get_card(self, account_id):
        return self._get(f"/v1/players/{account_id}/card")

    # --- Assets ---
    def get_heroes(self):
        return self._get("/v1/assets/heroes")