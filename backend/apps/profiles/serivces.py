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
            elif self.account.platform == "lol":
                self._sync_lol()
        except requests.Timeout:
            raise ExternalServiceUnavailable("Внешний сервис не отвечает, попробуй позже")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise SyncError("Аккаунт не найден на платформе — проверь ID")
            raise ExternalServiceUnavailable("Ошибка внешнего сервиса, попробуй позже")

        self.account.verified = True
        self.account.last_synced_at = timezone.now()
        self.account.save(update_fields=["verified", "last_synced_at"])


    def _sync_lol(self):
        from .integrations.riot_client import RiotClient
        client = RiotClient()

        # external_id хранится в формате "GameName#TAG"
        game_name, tag_line = self.account.external_id.split("#")
        account = client.get_account_by_riot_id(game_name, tag_line)
        puuid = account["puuid"]

        summoner = client.get_summoner_by_puuid(puuid)
        ranked = client.get_ranked_stats(summoner["id"])

        solo_queue = next((r for r in ranked if r.get("queueType") == "RANKED_SOLO_5x5"), None)

        match_ids = client.get_match_history(puuid, count=10)
        recent_form = []
        for match_id in match_ids[:10]:
            try:
                match = client.get_match_details(match_id)
                participant = next(
                    p for p in match["info"]["participants"] if p["puuid"] == puuid
                )
                recent_form.append({
                    "won": participant["win"],
                    "champion": participant["championName"],
                    "kda": f"{participant['kills']}/{participant['deaths']}/{participant['assists']}",
                })
            except Exception:
                continue  # если один матч не подтянулся — не роняем весь синк

        wins = solo_queue.get("wins", 0) if solo_queue else 0
        losses = solo_queue.get("losses", 0) if solo_queue else 0
        total = wins + losses
        winrate = round(wins / total * 100, 1) if total else 0

        self.account.extra_stats = {
            "tier": solo_queue.get("tier") if solo_queue else None,
            "rank": solo_queue.get("rank") if solo_queue else None,
            "lp": solo_queue.get("leaguePoints") if solo_queue else None,
            "wins": wins,
            "losses": losses,
            "matches": total,
            "winrate": winrate,
            "recent_form": recent_form,
        }
        self.account.game_label = "League of Legends"
        self.account.nickname = f"{game_name}#{tag_line}"
        self.account.save(update_fields=["extra_stats", "game_label", "nickname"])


    def _sync_pubg(self):
        from .integrations.pubg_client import PubgClient
        client = PubgClient()

        player = client.get_player(self.account.external_id)
        season_id = client.get_current_season_id()
        stats = client.get_season_stats(player["id"], season_id)

        game_modes = stats.get("data", {}).get("attributes", {}).get("gameModeStats", {})
        squad = game_modes.get("squad-fpp", {}) or game_modes.get("squad", {})

        kills = squad.get("kills", 0)
        wins = squad.get("wins", 0)
        rounds = squad.get("roundsPlayed", 0)
        top10s = squad.get("top10s", 0)
        kd = round(kills / max(rounds - wins, 1), 2)
        winrate = round(wins / rounds * 100, 1) if rounds else 0

        self.account.extra_stats = {
            "matches": rounds,
            "wins": wins,
            "top10s": top10s,
            "kills": kills,
            "kd": kd,
            "winrate": winrate,
        }
        self.account.game_label = "PUBG"
        self.account.nickname = player.get("attributes", {}).get("name", "")
        self.account.save(update_fields=["extra_stats", "game_label", "nickname"])

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
                    game_account=self.account, appid=game["appid"], date=today,
                    defaults={"game_name": game.get("name", "Unknown"), "playtime_forever": game.get("playtime_forever", 0)},
                )

        has_cs2 = any(g["appid"] == 730 for g in games)
        if has_cs2:
            cs2_stats = client.get_cs2_stats(self.account.external_id)
            if cs2_stats:
                stats_map = {s["name"]: s["value"] for s in cs2_stats}
                kills = stats_map.get("total_kills", 0)
                deaths = stats_map.get("total_deaths", 0)
                existing = self.account.extra_stats or {}
                existing["steam_cs2"] = {
                    "kills": kills, "deaths": deaths,
                    "kd": round(kills / max(deaths, 1), 2),
                    "wins": stats_map.get("total_wins", 0),
                }
                self.account.extra_stats = existing
                self.account.save(update_fields=["extra_stats"])

    def _sync_opendota(self):
        client = OpenDotaClient()

        wl = client.get_win_loss(self.account.external_id)
        player = client.get_player(self.account.external_id)
        heroes_raw = client.get_heroes(self.account.external_id)
        hero_names = client.get_hero_names()
        recent_matches = client.get_recent_matches(self.account.external_id, limit=10)

        wins = wl.get("win", 0)
        losses = wl.get("lose", 0)
        total_matches = wins + losses
        winrate = round(wins / total_matches * 100, 1) if total_matches else 0

        top_heroes = sorted(heroes_raw, key=lambda h: h.get("games", 0), reverse=True)[:5]
        top_heroes_data = [
            {
                "name": hero_names.get(h["hero_id"], f"Hero {h['hero_id']}"),
                "games": h.get("games", 0),
                "win": h.get("win", 0),
                "winrate": round(h["win"] / h["games"] * 100, 1) if h.get("games") else 0,
            }
            for h in top_heroes if h.get("games", 0) > 0
        ]

        recent_form = []
        for m in recent_matches[:10]:
            is_radiant = m.get("player_slot", 0) < 128
            radiant_win = m.get("radiant_win")
            won = (is_radiant and radiant_win) or (not is_radiant and not radiant_win)
            recent_form.append({
                "won": won,
                "hero": hero_names.get(m.get("hero_id"), "?"),
                "kda": f"{m.get('kills', 0)}/{m.get('deaths', 0)}/{m.get('assists', 0)}",
                "duration_min": round(m.get("duration", 0) / 60),
            })

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
            "recent_form": recent_form,
        }
        self.account.skill_rating = mmr_estimate
        self.account.game_label = "Dota 2"
        self.account.save(update_fields=["extra_stats", "skill_rating", "game_label"])

        today = timezone.now().date()
        DailySnapshot.objects.update_or_create(
            game_account=self.account, appid=570, date=today,
            defaults={"game_name": "Dota 2", "playtime_forever": 0},
        )

    def _sync_faceit(self):
        client = FaceitClient()
        player = client.get_player_by_nickname(self.account.external_id)
        stats = client.get_player_stats(player["player_id"])
        matches = client.get_recent_matches(player["player_id"], limit=10)

        lifetime = stats.get("lifetime", {})
        match_count = int(lifetime.get("Matches", 0))
        wins = int(lifetime.get("Wins", 0))
        winrate = float(lifetime.get("Win Rate %", 0))
        avg_kd = float(lifetime.get("Average K/D Ratio", 0))
        avg_hs = float(lifetime.get("Average Headshots %", 0))
        current_streak = int(lifetime.get("Current Win Streak", 0))
        longest_streak = int(lifetime.get("Longest Win Streak", 0))

        elo = player.get("games", {}).get("cs2", {}).get("faceit_elo")
        skill_level = player.get("games", {}).get("cs2", {}).get("skill_level")

        recent_form = []
        for m in matches.get("items", [])[:10]:
            recent_form.append({
                "map": m.get("game_map") or m.get("teams", {}).get("faction1", {}).get("nickname", "?"),
                "finished_at": m.get("finished_at"),
            })

        self.account.extra_stats = {
            "matches": match_count,
            "wins": wins,
            "winrate": winrate,
            "avg_kd": avg_kd,
            "avg_headshots": avg_hs,
            "current_streak": current_streak,
            "longest_streak": longest_streak,
            "elo": elo,
            "skill_level": skill_level,
            "recent_form": recent_form,
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
            "badge": None,
            "list_title": "Любимые герои",
            "list": [
                {"name": h["name"], "sub": f"{h['games']} игр", "value": f"{h['winrate']}%", "good": h["winrate"] >= 50}
                for h in extra_stats.get("top_heroes", [])
            ],
            "recent_form": [
                {"label": f["hero"], "sub": f"{f['kda']} · {f['duration_min']}м", "won": f["won"]}
                for f in extra_stats.get("recent_form", [])
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
            "recent_form": [
                {"label": f.get("map", "Матч"), "sub": "", "won": None}
                for f in extra_stats.get("recent_form", [])
            ],
        }
    if platform == "pubg":
        return {
            "game_label": "PUBG",
            "metrics": [
                {"label": "матчей", "value": extra_stats.get("matches", 0)},
                {"label": "побед", "value": extra_stats.get("wins", 0), "tone": "win"},
                {"label": "топ-10", "value": extra_stats.get("top10s", 0)},
                {"label": "K/D", "value": extra_stats.get("kd", 0), "tone": "accent"},
            ],
            "badge": None,
            "list_title": "Статистика",
            "list": [
                {"name": "Всего убийств", "sub": "", "value": extra_stats.get("kills", 0)},
                {"name": "Винрейт", "sub": "", "value": f"{extra_stats.get('winrate', 0)}%"},
            ],
            "recent_form": [],
        }
    if platform == "lol":
        return {
            "game_label": "League of Legends",
            "metrics": [
                {"label": "матчей", "value": extra_stats.get("matches", 0)},
                {"label": "побед", "value": extra_stats.get("wins", 0), "tone": "win"},
                {"label": "поражений", "value": extra_stats.get("losses", 0), "tone": "loss"},
                {"label": "винрейт", "value": f"{extra_stats.get('winrate', 0)}%", "tone": "accent"},
            ],
            "badge": f"{extra_stats.get('tier', '')} {extra_stats.get('rank', '')}".strip() or "Unranked",
            "list_title": "Ранг",
            "list": [
                {"name": "LP", "sub": "", "value": extra_stats.get("lp", 0)},
            ],
            "recent_form": [
                {"label": f["champion"], "sub": f["kda"], "won": f["won"]}
                for f in extra_stats.get("recent_form", [])
            ],
        }

    return None