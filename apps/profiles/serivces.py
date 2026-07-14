from datetime import date, timedelta
from django.db import transaction
from django.utils import timezone
import requests

from .models import GameAccount, DailySnapshot
from .integrations.steam_client import SteamClient
from .integrations.opendota_client import OpenDotaClient
from .integrations.faceit_client import FaceitClient


class SyncError(Exception):
    pass


class PrivateProfileError(SyncError):
    pass


class ExternalServiceUnavailable(SyncError):
    pass


class ProfileSyncService:
    def __init__(self, game_account: GameAccount):
        self.account = game_account

    def sync(self):
        try:
            if self.account.platform == "steam":
                self._sync_steam()
            elif self.account.platform == "opendota":
                self._sync_opendota()
            elif self.account.platform == "faceit":
                self._sync_faceit()
        except requests.Timeout:
            raise ExternalServiceUnavailable("Внешний сервис не отвечает, попробуй позже")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise SyncError("Аккаунт не найден на платформе — проверь ID")
            raise ExternalServiceUnavailable("Ошибка внешнего сервиса, попробуй позже")

        self.account.verified = True
        self.account.last_synced_at = timezone.now()
        self.account.save(update_fields=["verified", "last_synced_at"])

    def _sync_steam(self):
        client = SteamClient()
        games = client.get_owned_games(self.account.external_id)
        if not games:
            raise PrivateProfileError(
                "Не удалось получить игры — профиль приватный или пуст. "
                "Открой профиль в настройках приватности Steam."
            )
        today = date.today()
        with transaction.atomic():
            for game in games:
                DailySnapshot.objects.update_or_create(
                    game_account=self.account,
                    appid=game["appid"],
                    date=today,
                    defaults={
                        "game_name": game.get("name", "Unknown"),
                        "playtime_forever": game.get("playtime_forever", 0),
                    },
                )

    def _sync_opendota(self):
        client = OpenDotaClient()
        wl = client.get_win_loss(self.account.external_id)
        today = date.today()
        total_minutes_estimate = (wl.get("win", 0) + wl.get("lose", 0)) * 40

        DailySnapshot.objects.update_or_create(
            game_account=self.account,
            appid=570,
            date=today,
            defaults={"game_name": "Dota 2", "playtime_forever": total_minutes_estimate},
        )

    def _sync_faceit(self):
        client = FaceitClient()
        stats = client.get_player_stats(self.account.external_id)
        today = date.today()
        matches_played = int(stats.get("lifetime", {}).get("Matches", 0))
        estimated_minutes = matches_played * 35

        DailySnapshot.objects.update_or_create(
            game_account=self.account,
            appid=730,
            date=today,
            defaults={"game_name": "CS2", "playtime_forever": estimated_minutes},
        )


def get_daily_playtime(game_account: GameAccount, appid: int, target_date: date):
    today_snap = DailySnapshot.objects.filter(
        game_account=game_account, appid=appid, date=target_date
    ).first()
    yesterday_snap = DailySnapshot.objects.filter(
        game_account=game_account, appid=appid, date=target_date - timedelta(days=1)
    ).first()

    if not today_snap or not yesterday_snap:
        return None
    return max(today_snap.playtime_forever - yesterday_snap.playtime_forever, 0)


def get_account_summary(game_account: GameAccount):
    snapshots = game_account.snapshots.all()
    if not snapshots:
        return {"total_playtime": 0, "most_played_game": None, "games_count": 0}

    total = sum(s.playtime_forever for s in snapshots)
    most_played = max(snapshots, key=lambda s: s.playtime_forever)
    games_count = snapshots.values("appid").distinct().count()

    return {
        "total_playtime": total,
        "most_played_game": most_played.game_name,
        "games_count": games_count,
    }