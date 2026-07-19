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

        steam_id = self.account.user.profile.steam_id

        if not steam_id:
            raise SyncError("Steam аккаунт не привязан")

        games = client.get_owned_games(steam_id)

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

        self.account.save(update_fields=["nickname", "avatar"])

    def _sync_opendota(self):
        client = OpenDotaClient()

        wl = client.get_win_loss(self.account.external_id)
        player = client.get_player(self.account.external_id)
        heroes_raw = client.get_heroes(self.account.external_id)
        hero_names = client.get_hero_names()

        wins = wl.get("win", 0)
        losses = wl.get("lose", 0)
        total_matches = wins + losses
        winrate = round(wins / total_matches * 100, 1) if total_matches else 0

        
        top_heroes = sorted(heroes_raw, key=lambda h: h.get("games", 0), reverse=True)[:10]
        top_heroes_data = [
            {
                "name": hero_names.get(h["hero_id"], f"Hero {h['hero_id']}"),
                "games": h.get("games", 0),
                "win": h.get("win", 0),
                "winrate": round(h["win"] / h["games"] * 100, 1) if h.get("games") else 0,
            }
            for h in top_heroes if h.get("games", 0) > 0
        ]

        mmr_estimate = player.get("mmr_estimate", {}).get("estimate")
        rank_tier = player.get("rank_tier")  

        self.account.extra_stats = {
            "total_matches": total_matches,
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "top_heroes": top_heroes_data,
            "mmr_estimate": mmr_estimate,
            "rank_tier": rank_tier,
        }
        self.account.skill_rating = mmr_estimate
        self.account.game_label = "Dota 2"
        self.account.save(update_fields=["extra_stats", "skill_rating", "game_label"])

        
        today = timezone.now().date()
        DailySnapshot.objects.update_or_create(
            game_account=self.account,
            appid=570,
            date=today,
            defaults={"game_name": "Dota 2", "playtime_forever": 0},
        )

    def _sync_faceit(self):
        client = FaceitClient()
        player = client.get_player_by_nickname(self.account.external_id)
        stats = client.get_player_stats(player["player_id"])

        lifetime = stats.get("lifetime", {})
        matches = int(lifetime.get("Matches", 0))
        wins = int(lifetime.get("Wins", 0))
        winrate = float(lifetime.get("Win Rate %", 0))
        avg_kd = float(lifetime.get("Average K/D Ratio", 0))
        avg_hs = float(lifetime.get("Average Headshots %", 0))
        current_streak = int(lifetime.get("Current Win Streak", 0))
        longest_streak = int(lifetime.get("Longest Win Streak", 0))

        elo = player.get("games", {}).get("cs2", {}).get("faceit_elo")
        skill_level = player.get("games", {}).get("cs2", {}).get("skill_level")

        self.account.extra_stats = {
            "matches": matches,
            "wins": wins,
            "winrate": winrate,
            "avg_kd": avg_kd,
            "avg_headshots": avg_hs,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "elo": elo,
            "skill_level": skill_level,
        }
        self.account.skill_rating = elo
        self.account.game_label = "CS2"
        self.account.nickname = player.get("nickname", "")
        self.account.avatar = player.get("avatar", "")
        self.account.save(update_fields=["extra_stats", "skill_rating", "game_label", "nickname", "avatar"])


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


def build_display_stats(platform, extra_stats):
    """Приводит статистику разных платформ к единому формату для фронта"""
    if not extra_stats:
        return None

    if platform == "opendota":
        return {
            "game_label": "Dota 2",
            "metrics": [
                {"label": "матчей", "value": extra_stats.get("total_matches", 0)},
                {"label": "побед", "value": extra_stats.get("wins", 0), "tone": "win"},
                {"label": "поражений", "value": extra_stats.get("losses", 0), "tone": "loss"},
                {"label": "винрейт", "value": f"{extra_stats.get('winrate', 0)}%", "tone": "accent"},
            ],
            "badge": None,  # заполняется во view с учётом rank_tier
            "list_title": "Любимые герои",
            "list": [
                {"name": h["name"], "sub": f"{h['games']} игр", "value": f"{h['winrate']}%", "good": h["winrate"] >= 50}
                for h in extra_stats.get("top_heroes", [])
            ],
        }

    if platform == "faceit":
        return {
            "game_label": "CS2",
            "metrics": [
                {"label": "матчей", "value": extra_stats.get("matches", 0)},
                {"label": "побед", "value": extra_stats.get("wins", 0), "tone": "win"},
                {"label": "винрейт", "value": f"{extra_stats.get('winrate', 0)}%", "tone": "accent"},
                {"label": "K/D", "value": extra_stats.get("avg_kd", 0)},
            ],
            "badge": f"Level {extra_stats.get('skill_level')}" if extra_stats.get("skill_level") else None,
            "list_title": "Дополнительно",
            "list": [
                {"name": "Средний HS%", "sub": "", "value": f"{extra_stats.get('avg_headshots', 0)}%"},
                {"name": "Текущая серия побед", "sub": "", "value": extra_stats.get("current_streak", 0)},
                {"name": "Лучшая серия", "sub": "", "value": extra_stats.get("longest_streak", 0)},
            ],
        }

    return None