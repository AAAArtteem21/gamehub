from datetime import date, timedelta
from django.db import transaction
from django.utils import timezone
import requests

from .models import GameAccount, DailySnapshot
from .integrations.steam_client import SteamClient
from .integrations.opendota_client import OpenDotaClient
from .integrations.faceit_client import FaceitClient
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from django.core.cache import cache
from django.db import IntegrityError, transaction


DEADLOCK_APPID = 1422450


def _format_match_time(seconds):
    if seconds is None:
        return None
    sign = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    m, s = divmod(seconds, 60)
    return f"{sign}{m}:{s:02d}"


def _extract_items_with_timing(my_slot, item_names):
    purchase_log = my_slot.get("purchase_log") or []
    items = []
    for slot in range(6):
        item_id = my_slot.get(f"item_{slot}")
        if not item_id or item_id not in item_names:
            continue
        info = item_names[item_id]
        bought_at = None
        for entry in reversed(purchase_log):
            if entry.get("key") == info["key"]:
                bought_at = entry.get("time")
                break
        items.append({
            "name": info["name"],
            "icon_url": info["icon_url"],
            "bought_at": _format_match_time(bought_at),
        })
    return items


def _compute_match_verdict(my_slot, won):
    kills = my_slot.get("kills", 0)
    deaths = my_slot.get("deaths", 0)
    assists = my_slot.get("assists", 0)
    kda = (kills + assists) / max(deaths, 1)

    if not won and deaths >= 10 and kda < 1:
        return {"label": "Соляново", "tone": "terrible"}
    if kda >= 6:
        return {"label": "Огромный импакт", "tone": "great"}
    if kda >= 3.5:
        return {"label": "Хорошая игра", "tone": "good"}
    if kda >= 1.8:
        return {"label": "Нормально", "tone": "neutral"}
    if kda >= 0.8:
        return {"label": "Слабая игра", "tone": "bad"}
    return {"label": "зачем тролишь?", "tone": "terrible"}

def _compute_valorant_verdict(kills, deaths, assists, acs):
    kda = (kills + assists) / max(deaths, 1)
    if acs >= 280 and kda >= 2:
        return {"label": "Огромный импакт", "tone": "great"}
    if acs >= 220:
        return {"label": "Хорошая игра", "tone": "good"}
    if acs >= 150:
        return {"label": "Нормально", "tone": "neutral"}
    if acs >= 100:
        return {"label": "Слабая игра", "tone": "bad"}
    return {"label": "Ужасная игра", "tone": "terrible"}

class SyncError(Exception):
    pass


class PrivateProfileError(SyncError):
    pass


class ExternalServiceUnavailable(SyncError):
    pass


class ProfileSyncService:
    def __init__(self, game_account: GameAccount):
        self.account = game_account
        self.linked_accounts = []

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
            elif self.account.platform == "valorant":
                self._sync_valorant()
            elif self.account.platform == "pubg":
                self._sync_pubg()
            elif self.account.platform == "roblox":
                self._sync_roblox()
            elif self.account.platform == "fortnite":
                self._sync_fortnite()
            elif self.account.platform == "deadlock":
                self._sync_deadlock()
        except requests.Timeout:
            raise ExternalServiceUnavailable("Внешний сервис не отвечает, попробуй позже")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise SyncError("Аккаунт не найден на платформе — проверь ID")
            raise ExternalServiceUnavailable("Ошибка внешнего сервиса, попробуй позже")

        self.account.verified = True
        self.account.last_synced_at = timezone.now()
        self.account.save(update_fields=["verified", "last_synced_at"])

    def _spawn_background_sync(self, account: GameAccount):
        """Фоновый синк одного аккаунта — как _run_sync_in_background во views."""
        def _run():
            try:
                ProfileSyncService(account).sync()
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()

    def _auto_link_steam_accounts(self, games):
        """
        После _sync_steam: создаём opendota / deadlock / faceit без дублей.
        Ошибки любой платформы НЕ роняют Steam-синк.
        Синки новых аккаунтов — в фоне.
        """
        user = self.account.user
        steam_id = self.account.external_id
        account_id = int(steam_id) & 0xFFFFFFFF  # тот же расчёт, что у OpenDota
        self.linked_accounts = []

        appids = {g["appid"]: g for g in games}

        def _link(platform, external_id):
            if GameAccount.objects.filter(user=user, platform=platform).exists():
                return None
            try:
                acc = GameAccount.objects.create(
                    user=user, platform=platform, external_id=str(external_id)
                )
            except IntegrityError:
                return None
            self.linked_accounts.append(acc)
            return acc

        # --- Dota 2 → OpenDota (только если игра есть в библиотеке) ---
        if 570 in appids:
            acc = _link("opendota", account_id)
            if acc:
                self._spawn_background_sync(acc)

        # --- Deadlock (часы сразу из owned games, стату — в фоне) ---
        if DEADLOCK_APPID in appids:
            acc = _link("deadlock", account_id)
            if acc:
                hours = round(appids[DEADLOCK_APPID].get("playtime_forever", 0) / 60, 1)
                acc.extra_stats = {"hours_played": hours, "match_history": []}
                acc.game_label = "Deadlock"
                acc.save(update_fields=["extra_stats", "game_label"])
                self._spawn_background_sync(acc)

        # --- Faceit по SteamID (может отсутствовать — это нормально) ---
        neg_cache_key = f"faceit_neg_by_steam:{steam_id}"
        if not cache.get(neg_cache_key):
            try:
                from .integrations.faceit_client import FaceitClient
                player = FaceitClient().get_player_by_steam_id(steam_id)
                player_id = (player or {}).get("player_id")
                if player_id:
                    acc = _link("faceit", player.get("nickname") or player_id)
                    if acc:
                        acc.extra_stats = {"player_id": player_id}
                        acc.save(update_fields=["extra_stats"])
                        self._spawn_background_sync(acc)
                else:
                    cache.set(neg_cache_key, True, timeout=3600)  # не долбим повторно час
            except Exception:
                pass  # нет ключа Faceit / 404 / rate limit — Steam-синк не валим

    def _sync_deadlock(self):
        """Deadlock: rank + match-history. account-stats/mate-stats часто 403 без ключа — не роняем синк."""
        from collections import Counter
        from datetime import datetime
        from django.core.cache import cache
        from django.utils import timezone
        from .integrations.deadlock_client import (
            DeadlockClient,
            DeadlockError,
            DeadlockRateLimited,
        )

        raw_id = str(self.account.external_id or "").strip()
        if raw_id.startswith("7656119"):
            account_id = str(int(raw_id) & 0xFFFFFFFF)
            self.account.external_id = account_id
            self.account.save(update_fields=["external_id"])
        else:
            account_id = raw_id

        if not account_id.isdigit():
            raise SyncError("Deadlock: укажи Steam32 account id (число)")

        client = DeadlockClient()
        cache_key = f"deadlock:player:{account_id}:v2"
        cached = cache.get(cache_key)

        if cached is None:
            try:
                rank_raw = client.get_rank(account_id) or {}
            except DeadlockRateLimited:
                raise SyncError("Deadlock API: лимит запросов, подожди минуту")
            except (DeadlockError, Exception):
                rank_raw = {}

            try:
                matches_raw = client.get_match_history(account_id) or []
            except DeadlockRateLimited:
                raise SyncError("Deadlock API: лимит запросов, подожди минуту")
            except DeadlockError as e:
                raise SyncError(str(e))
            except Exception as e:
                raise SyncError(f"Deadlock history: {e}")

            if isinstance(matches_raw, dict):
                matches_raw = (
                    matches_raw.get("matches")
                    or matches_raw.get("data")
                    or matches_raw.get("history")
                    or []
                )
            if not isinstance(matches_raw, list):
                matches_raw = []

            # опционально — 403 не должен валить синк
            hero_stats_raw = []
            try:
                if hasattr(client, "get_hero_stats"):
                    hero_stats_raw = client.get_hero_stats(account_id) or []
            except Exception:
                hero_stats_raw = []

            cached = {
                "rank": rank_raw if isinstance(rank_raw, dict) else {},
                "matches": matches_raw,
                "hero_stats": hero_stats_raw if isinstance(hero_stats_raw, list) else [],
            }
            cache.set(cache_key, cached, 600)

        rank_raw = cached.get("rank") or {}
        matches_raw = cached.get("matches") or []
        hero_stats_raw = cached.get("hero_stats") or []

        # --- rank ---
        badge = rank_raw.get("badge") or rank_raw.get("rank") or 0
        subrank = rank_raw.get("subrank") or 0
        try:
            badge = int(badge)
        except (TypeError, ValueError):
            badge = 0
        try:
            subrank = int(subrank)
        except (TypeError, ValueError):
            subrank = 0

        tier = None
        rdb = rank_raw.get("ranked_display_badge")
        if isinstance(rdb, dict):
            tier = rdb.get("name") or rdb.get("text") or rdb.get("label")
        elif isinstance(rdb, str) and rdb.strip():
            tier = rdb.strip()
        if not tier and badge:
            tier = f"Badge {badge}" + (f".{subrank}" if subrank else "")
        if not tier:
            tier = "Unranked"

        # --- hero names ---
        hero_names = cache.get("deadlock:hero_names") or {}
        if hero_names and any(not isinstance(k, str) for k in hero_names.keys()):
            hero_names = {str(k): v for k, v in hero_names.items()}
            cache.set("deadlock:hero_names", hero_names, 3600)

        if not hero_names:
            try:
                heroes = client.get_heroes() or []
                if isinstance(heroes, dict):
                    heroes = heroes.get("heroes") or heroes.get("data") or []
                if isinstance(heroes, list):
                    hero_names = {}
                    for h in heroes:
                        if not isinstance(h, dict):
                            continue
                        hid = h.get("id") if h.get("id") is not None else h.get("hero_id")
                        if hid is None:
                            continue
                        name = (
                            h.get("name")
                            or h.get("display_name")
                            or h.get("class_name")
                            or h.get("localized_name")
                            or str(hid)
                        )
                        name = str(name).replace("hero_", "").replace("_", " ").title()
                        hero_names[str(hid)] = name
                    if hero_names:
                        cache.set("deadlock:hero_names", hero_names, 3600)
            except Exception:
                hero_names = {}

        def _won(m: dict):
            outcome = m.get("player_match_outcome")
            if outcome is not None:
                # часто 1 = win, 0 = loss; либо строка
                if outcome in (1, True, "win", "Won", "WIN"):
                    return True
                if outcome in (0, 2, False, "loss", "Loss", "LOSE", "lost"):
                    return False
            if m.get("player_won") is not None:
                return bool(m["player_won"])
            pt, mr = m.get("player_team"), m.get("match_result")
            if pt is not None and mr is not None:
                try:
                    return int(pt) == int(mr)
                except (TypeError, ValueError):
                    pass
            return None

        def _kda(m: dict):
            k = m.get("player_kills", m.get("kills", 0)) or 0
            d = m.get("player_deaths", m.get("deaths", 0)) or 0
            a = m.get("player_assists", m.get("assists", 0)) or 0
            try:
                return int(k), int(d), int(a)
            except (TypeError, ValueError):
                return 0, 0, 0

        match_history = []
        hero_counter = Counter()
        wins = losses = 0
        k_sum = d_sum = a_sum = n_kda = 0
        nw_sum = nw_n = 0

        for m in matches_raw[:40]:
            if not isinstance(m, dict):
                continue

            hid = m.get("hero_id")
            hname = hero_names.get(str(hid), f"Hero {hid}" if hid is not None else "?")
            won = _won(m)
            k, d, a = _kda(m)

            if won is True:
                wins += 1
            elif won is False:
                losses += 1

            k_sum += k
            d_sum += d
            a_sum += a
            n_kda += 1
            if hname and hname != "?":
                hero_counter[hname] += 1

            mid = m.get("match_id") or m.get("id")
            dur_s = m.get("match_duration_s") or m.get("duration_s") or m.get("duration")
            duration = None
            if dur_s is not None:
                try:
                    sec = int(dur_s)
                    duration = f"{sec // 60}:{sec % 60:02d}"
                except (TypeError, ValueError):
                    duration = None

            played_at = None
            ts = m.get("start_time") or m.get("match_start")
            if ts is not None:
                try:
                    played_at = datetime.utcfromtimestamp(int(ts)).strftime("%d.%m.%Y")
                except Exception:
                    played_at = str(ts)

            nw = m.get("net_worth")
            if nw is not None:
                try:
                    nw_sum += int(nw)
                    nw_n += 1
                except (TypeError, ValueError):
                    pass

            level = m.get("hero_level") or m.get("level")
            delta = m.get("ranked_delta")

            details = [
                {"label": "Net worth", "value": nw if nw is not None else "—"},
                {"label": "Уровень", "value": level if level is not None else "—"},
                {"label": "Last hits", "value": m.get("last_hits", "—")},
                {"label": "Denies", "value": m.get("denies", "—")},
            ]
            if delta is not None:
                details.append({"label": "Ranked Δ", "value": delta})

            match_history.append({
                "won": won,
                "title": hname,
                "subtitle": f"{k}/{d}/{a}",
                "duration": duration,
                "match_id": str(mid) if mid is not None else None,
                "played_at": played_at,
                "verdict": None,
                "details": details,
            })

        total = wins + losses
        winrate = round(wins / total * 100, 1) if total else 0

        avg_kda = None
        if n_kda:
            ratio = round((k_sum + a_sum) / max(d_sum, 1), 2)
            avg_kda = (
                f"{round(k_sum / n_kda, 1)}/"
                f"{round(d_sum / n_kda, 1)}/"
                f"{round(a_sum / n_kda, 1)} ({ratio})"
            )

        avg_nw = round(nw_sum / nw_n) if nw_n else None

        top_heroes = [{"name": n, "games": c} for n, c in hero_counter.most_common(8)]

        # hero_stats API — если вдруг отдал
        if not top_heroes and hero_stats_raw:
            for h in hero_stats_raw[:8]:
                if not isinstance(h, dict):
                    continue
                hid = h.get("hero_id") or h.get("id")
                name = hero_names.get(str(hid), h.get("hero_name") or f"Hero {hid}")
                games = h.get("matches") or h.get("games") or h.get("matches_played") or 0
                top_heroes.append({"name": name, "games": games})

        recent_form = [
            ("W" if m["won"] else "L")
            for m in match_history
            if m.get("won") is not None
        ][:10]

        self.account.extra_stats = {
            "matches": total if total else len(match_history),
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "tier": tier,
            "badge": badge,
            "subrank": subrank,
            "avg_kda": avg_kda,
            "avg_net_worth": avg_nw,
            "top_heroes": top_heroes,
            "recent_form": recent_form,
            "match_history": match_history,
        }
        self.account.game_label = "Deadlock"
        self.account.skill_rating = badge or None
        self.account.verified = True
        self.account.last_synced_at = timezone.now()
        self.account.save(
            update_fields=[
                "extra_stats",
                "game_label",
                "skill_rating",
                "verified",
                "last_synced_at",
                "external_id",
            ]
        )

    def _sync_lol(self):
        from .integrations.riot_client import RiotClient, RiotError
        from datetime import datetime
        from collections import Counter

        raw = (self.account.external_id or "").strip()
        if "#" not in raw:
            raise SyncError("Riot ID в формате Ник#Тег")
        name, tag = raw.split("#", 1)
        platform = (self.account.extra_stats or {}).get("riot_platform") or "euw1"

        client = RiotClient(platform=platform)
        try:
            acc = client.get_account_by_riot_id(name, tag)
            puuid = acc["puuid"]
            leagues = client.get_league_by_puuid(puuid) or []
            match_ids = client.get_match_ids(puuid, count=20) or []
        except RiotError as e:
            raise SyncError(str(e))

        queues = {}
        for entry in leagues:
            qt = entry.get("queueType") or "OTHER"
            queues[qt] = {
                "tier": entry.get("tier"),
                "rank": entry.get("rank"),
                "lp": entry.get("leaguePoints"),
                "wins": int(entry.get("wins") or 0),
                "losses": int(entry.get("losses") or 0),
            }

        solo = queues.get("RANKED_SOLO_5x5") or {}
        flex = queues.get("RANKED_FLEX_SR") or {}
        wins = solo.get("wins", 0)
        losses = solo.get("losses", 0)
        total = wins + losses
        tier_str = None
        if solo.get("tier"):
            tier_str = f"{solo['tier']} {solo.get('rank') or ''}".strip()

        champ_counter = Counter()
        k_sum = d_sum = a_sum = n = 0
        history = []

        for mid in match_ids[:20]:
            try:
                detail = client.get_match(mid)
            except Exception:
                continue
            info = detail.get("info") or {}
            me = next((p for p in (info.get("participants") or []) if p.get("puuid") == puuid), None)
            if not me:
                continue

            champ = me.get("championName") or "?"
            champ_counter[champ] += 1
            k, d, a = int(me.get("kills") or 0), int(me.get("deaths") or 0), int(me.get("assists") or 0)
            k_sum += k
            d_sum += d
            a_sum += a
            n += 1

            cs = int(me.get("totalMinionsKilled") or 0) + int(me.get("neutralMinionsKilled") or 0)
            dmg = int(me.get("totalDamageDealtToChampions") or 0)
            gold = int(me.get("goldEarned") or 0)
            vision = int(me.get("visionScore") or 0)
            duration_sec = int(info.get("gameDuration") or 0)
            queue_id = info.get("queueId")
            queue_label = {
                420: "Solo/Duo",
                440: "Flex",
                450: "ARAM",
                400: "Normal",
                430: "Blind",
            }.get(queue_id, f"Q{queue_id}")

            ts = info.get("gameStartTimestamp")
            played_at = None
            if ts:
                try:
                    played_at = datetime.utcfromtimestamp(ts / 1000).strftime("%d.%m.%Y %H:%M")
                except Exception:
                    pass

            history.append({
                "won": bool(me.get("win")),
                "title": champ,
                "subtitle": f"{k}/{d}/{a} · {queue_label}",
                "match_id": mid,
                "played_at": played_at,
                "duration": f"{duration_sec // 60} мин" if duration_sec else None,
                "platform": "lol",
                "details": [
                    {"label": "Режим", "value": queue_label},
                    {"label": "CS", "value": cs},
                    {"label": "Урон", "value": f"{dmg:,}".replace(",", " ")},
                    {"label": "Золото", "value": f"{gold:,}".replace(",", " ")},
                    {"label": "Обзор", "value": vision},
                    {"label": "Уровень", "value": me.get("champLevel") or "—"},
                ],
            })

        avg_kda = None
        if n:
            ratio = round((k_sum + a_sum) / max(d_sum, 1), 2)
            avg_kda = f"{round(k_sum/n,1)}/{round(d_sum/n,1)}/{round(a_sum/n,1)} ({ratio})"

        top_champs = [
            {"name": name_, "games": cnt}
            for name_, cnt in champ_counter.most_common(5)
        ]

        self.account.extra_stats = {
            "matches": total,
            "wins": wins,
            "losses": losses,
            "winrate": round(wins / total * 100, 1) if total else 0,
            "tier": tier_str or "Unranked",
            "lp": solo.get("lp"),
            "flex_tier": (
                f"{flex['tier']} {flex.get('rank') or ''}".strip()
                if flex.get("tier") else None
            ),
            "flex_lp": flex.get("lp"),
            "flex_wins": flex.get("wins"),
            "flex_losses": flex.get("losses"),
            "riot_platform": platform,
            "puuid": puuid,
            "avg_kda": avg_kda,
            "main_agent": top_champs[0]["name"] if top_champs else None,
            "top_champions": top_champs,
            "queues": queues,
            "match_history": history,
            "recent_form": ["W" if m["won"] else "L" for m in history[:10]],
        }
        self.account.game_label = "League of Legends"
        self.account.nickname = f"{acc.get('gameName')}#{acc.get('tagLine')}"
        self.account.skill_rating = solo.get("lp")
        self.account.save(update_fields=["extra_stats", "game_label", "nickname", "skill_rating"])

    def _sync_valorant(self):
        from .integrations.valorant_client import ValorantClient
        client = ValorantClient()

        if "#" not in self.account.external_id:
            raise SyncError("Укажи Riot ID в формате Ник#Тег")

        name, tag = self.account.external_id.split("#", 1)

        try:
            account = client.get_account(name, tag)
        except ValueError as e:
            raise SyncError(str(e))

        region = account.get("region") or "eu"

        try:
            mmr = client.get_mmr(name, tag, region=region)
        except Exception:
            mmr = {}

        try:
            matches = client.get_matches(name, tag, region=region, size=40)
        except Exception:
            matches = []

        current_data = mmr.get("current_data") or {}
        current_tier = current_data.get("currenttierpatched", "Unranked")
        rr = current_data.get("ranking_in_tier", 0)

        match_history, agent_counter = [], {}
        for match in matches[:40]:
            players = (match.get("players") or {}).get("all_players") or []
            me = next((p for p in players if p.get("name", "").lower() == name.lower()), None)
            if not me:
                continue

            team_key = (me.get("team") or "").lower()
            team_won = (match.get("teams") or {}).get(team_key, {}).get("has_won", False)
            agent = me.get("character", "?")
            agent_counter[agent] = agent_counter.get(agent, 0) + 1

            stats = me.get("stats") or {}
            meta = match.get("metadata") or {}
            map_name = meta.get("map", "?")
            match_id = meta.get("matchid")
            rounds_played = meta.get("rounds_played") or 1
            acs = round(stats.get("score", 0) / max(rounds_played, 1))
            kills = stats.get("kills", 0)
            deaths = stats.get("deaths", 0)
            assists = stats.get("assists", 0)

            game_start = meta.get("game_start")
            played_at = None
            if game_start:
                ts = game_start / 1000 if game_start > 10_000_000_000 else game_start
                try:
                    played_at = datetime.fromtimestamp(ts).strftime("%d.%m.%Y")
                except (OSError, ValueError, OverflowError):
                    played_at = None

            game_length = meta.get("game_length")
            duration = f"{round(game_length / 60)} мин" if game_length else None

            match_history.append({
                "won": team_won,
                "title": agent,
                "subtitle": f"{kills}/{deaths}/{assists}",
                "duration": duration,
                "match_id": match_id,
                "played_at": played_at,
                "verdict": _compute_valorant_verdict(kills, deaths, assists, acs),
                "solo": None,
                "details": [
                    {"label": "Карта", "value": map_name},
                    {"label": "Combat Score (ACS)", "value": acs},
                    {"label": "Хедшоты", "value": stats.get("headshots", "—")},
                ],
            })

        main_agent = max(agent_counter, key=agent_counter.get) if agent_counter else None
        wins = sum(1 for m in match_history if m["won"])
        winrate = round(wins / len(match_history) * 100, 1) if match_history else 0

        # avg за последние игры — сами
        nk = nd = na = acs_sum = n_m = 0
        for m in match_history[:20]:
            parts = (m.get("subtitle") or "").split("/")
            if len(parts) >= 3:
                try:
                    nk += int(parts[0])
                    nd += int(parts[1])
                    na += int(str(parts[2]).split()[0])
                    n_m += 1
                except (TypeError, ValueError):
                    pass
            for det in m.get("details") or []:
                if det.get("label") == "Combat Score (ACS)":
                    try:
                        acs_sum += int(det.get("value") or 0)
                    except (TypeError, ValueError):
                        pass

        avg_kills = round(nk / n_m, 1) if n_m else None
        avg_deaths = round(nd / n_m, 1) if n_m else None
        avg_assists = round(na / n_m, 1) if n_m else None
        avg_acs = round(acs_sum / n_m) if n_m and acs_sum else None
        avg_kd = round((nk + na) / max(nd, 1), 2) if n_m else None

        self.account.extra_stats = {
            "matches": len(match_history),
            "wins": wins,
            "winrate": winrate,
            "tier": current_tier,
            "rr": rr,
            "main_agent": main_agent,
            "avg_kills": avg_kills,
            "avg_deaths": avg_deaths,
            "avg_assists": avg_assists,
            "avg_acs": avg_acs,
            "avg_kd_recent": avg_kd,
            "sample_size": n_m,
            "match_history": match_history,
        }
        self.account.game_label = "Valorant"
        self.account.nickname = f"{name}#{tag}"
        self.account.save(update_fields=["extra_stats", "game_label", "nickname"])

    def _sync_fortnite(self):
        from .integrations.fortnite_client import FortniteClient, FortniteError

        name = (self.account.external_id or "").strip()
        if not name:
            raise SyncError("Укажи Epic display name")

        client = FortniteClient()

        def pack_window(data: dict) -> dict:
            account = data.get("account") or {}
            bp = data.get("battlePass") or {}
            stats_all = ((data.get("stats") or {}).get("all") or {})
            overall = stats_all.get("overall") or {}

            def pack_mode(m):
                if not m:
                    return None
                wins = int(m.get("wins") or 0)
                matches = int(m.get("matches") or 0)
                return {
                    "wins": wins,
                    "matches": matches,
                    "kills": int(m.get("kills") or 0),
                    "deaths": int(m.get("deaths") or 0),
                    "kd": m.get("kd"),
                    "winrate": m.get("winRate") if m.get("winRate") is not None else (
                        round(wins / matches * 100, 1) if matches else 0
                    ),
                    "top3": m.get("top3"),
                    "top5": m.get("top5"),
                    "top6": m.get("top6"),
                    "top10": m.get("top10"),
                    "top12": m.get("top12"),
                    "top25": m.get("top25"),
                    "score": m.get("score"),
                    "score_per_match": m.get("scorePerMatch"),
                    "kills_per_match": m.get("killsPerMatch"),
                    "minutes": m.get("minutesPlayed"),
                    "players_outlived": m.get("playersOutlived"),
                }

            modes = {}
            for key in ("solo", "duo", "squad", "ltm"):
                p = pack_mode(stats_all.get(key))
                if p and p.get("matches"):
                    modes[key] = p

            o = pack_mode(overall) or {}
            return {
                "account_id": account.get("id"),
                "name": account.get("name") or name,
                "bp_level": bp.get("level"),
                "bp_progress": bp.get("progress"),
                "overall": o,
                "modes": modes,
                "input_pc": pack_mode(
                    (((data.get("stats") or {}).get("keyboardMouse") or {}).get("overall"))
                ),
                "input_gamepad": pack_mode(
                    (((data.get("stats") or {}).get("gamepad") or {}).get("overall"))
                ),
            }

        try:
            life_raw = client.get_br_stats(name, "lifetime")
            try:
                season_raw = client.get_br_stats(name, "season")
            except FortniteError:
                season_raw = {}
        except FortniteError as e:
            raise SyncError(str(e))

        lifetime = pack_window(life_raw)
        season = pack_window(season_raw) if season_raw else None
        o = lifetime.get("overall") or {}

        self.account.extra_stats = {
            # совместимость со старой карточкой
            "matches": o.get("matches", 0),
            "wins": o.get("wins", 0),
            "losses": max((o.get("matches") or 0) - (o.get("wins") or 0), 0),
            "winrate": o.get("winrate", 0),
            "kills": o.get("kills", 0),
            "deaths": o.get("deaths", 0),
            "kd": o.get("kd", 0),
            "bp_level": lifetime.get("bp_level"),
            "bp_progress": lifetime.get("bp_progress"),
            "modes": lifetime.get("modes") or {},
            # окна для UI
            "windows": {
                "lifetime": lifetime,
                "season": season,
            },
            "default_window": "season" if season and (season.get("overall") or {}).get("matches") else "lifetime",
            # PR/earnings — fortnite-api.com не отдаёт
            "pr": None,
            "earnings": None,
            "match_history": [],
        }
        self.account.game_label = "Fortnite"
        self.account.nickname = lifetime.get("name") or name
        self.account.save(update_fields=["extra_stats", "game_label", "nickname"])

    def _sync_pubg(self):
        from .integrations.pubg_client import PubgClient, PubgError
        import requests
        from django.conf import settings

        steam_id = (self.account.external_id or "").strip()
        if not steam_id.isdigit():
            raise SyncError("Для PUBG укажи SteamID64")

        client = PubgClient()
        try:
            minutes = client.get_playtime_minutes(steam_id)
            summary = client.get_player_summary(steam_id)
        except PubgError as e:
            raise SyncError(str(e))

        # playtime_2weeks из owned games
        minutes_2w = 0
        try:
            url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
            r = requests.get(
                url,
                params={
                    "key": settings.STEAM_API_KEY,
                    "steamid": steam_id,
                    "include_appinfo": 1,
                    "include_played_free_games": 1,
                },
                timeout=15,
            )
            r.raise_for_status()
            for g in r.json().get("response", {}).get("games") or []:
                if g.get("appid") == 578080:
                    minutes_2w = int(g.get("playtime_2weeks") or 0)
                    break
        except Exception:
            pass

        hours = round(minutes / 60, 1)
        hours_2w = round(minutes_2w / 60, 1)

        self.account.extra_stats = {
            "matches": 0,
            "wins": 0,
            "losses": 0,
            "winrate": 0,
            "hours_played": hours,
            "hours_2weeks": hours_2w,
            "minutes_forever": minutes,
            "steam_avatar": summary.get("avatarfull") or summary.get("avatarmedium"),
            "steam_country": summary.get("loccountrycode"),
            "steam_status": summary.get("personastate"),  # 0 offline … 1 online
            "source": "steam_playtime",
            "note": "Полная BR-стата (K/D, wins) — после ключа developer.pubg.com",
            "match_history": [],
        }
        self.account.game_label = "PUBG"
        self.account.nickname = summary.get("personaname") or steam_id
        if summary.get("avatarfull"):
            self.account.avatar = summary.get("avatarfull")
            self.account.save(
                update_fields=["extra_stats", "game_label", "nickname", "avatar"]
            )
        else:
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
            cs2_raw = client.get_cs2_stats(self.account.external_id)
            if cs2_raw:
                m = {s["name"]: s["value"] for s in cs2_raw}

                kills = m.get("total_kills", 0)
                deaths = m.get("total_deaths", 0)
                matches_played = m.get("total_matches_played", 0)
                matches_won = m.get("total_matches_won", 0)
                rounds_played = m.get("total_rounds_played", 0)
                round_wins = m.get("total_wins", 0)
                headshot_kills = m.get("total_kills_headshot", 0)
                shots_fired = m.get("total_shots_fired", 0)
                shots_hit = m.get("total_shots_hit", 0)

                weapon_names = {
                    "ak47": "AK-47", "awp": "AWP", "m4a1": "M4A1", "deagle": "Desert Eagle",
                    "glock": "Glock-18", "hkp2000": "P2000", "p250": "P250", "mp9": "MP9",
                    "mac10": "MAC-10", "famas": "FAMAS", "galilar": "Galil AR", "sg556": "SG 553",
                    "scar20": "SCAR-20", "ssg08": "SSG 08", "mp7": "MP7", "nova": "Nova",
                    "negev": "Negev", "sawedoff": "Sawed-Off", "bizon": "PP-Bizon", "tec9": "Tec-9",
                    "mag7": "MAG-7", "xm1014": "XM1014", "elite": "Dual Berettas",
                    "fiveseven": "Five-SeveN", "ump45": "UMP-45", "p90": "P90", "knife": "Нож",
                }
                weapon_kills = {w: m.get(f"total_kills_{w}", 0) for w in weapon_names}
                top_weapon_key = max(weapon_kills, key=weapon_kills.get, default=None)
                top_weapon = {
                    "name": weapon_names.get(top_weapon_key, "—"),
                    "kills": weapon_kills.get(top_weapon_key, 0),
                } if top_weapon_key else None

                map_names = {
                    "de_dust2": "Dust II", "de_inferno": "Inferno", "de_nuke": "Nuke",
                    "de_train": "Train", "de_vertigo": "Vertigo", "de_cbble": "Cobblestone",
                    "de_lake": "Lake", "de_safehouse": "Safehouse", "cs_office": "Office",
                    "cs_italy": "Italy",
                }
                top_maps = []
                for map_key, map_label in map_names.items():
                    rounds = m.get(f"total_rounds_map_{map_key}", 0)
                    wins = m.get(f"total_wins_map_{map_key}", 0)
                    if rounds > 0:
                        top_maps.append({
                            "name": map_label, "rounds": rounds,
                            "winrate": round(wins / rounds * 100, 1),
                        })
                top_maps.sort(key=lambda x: x["rounds"], reverse=True)
                top_maps = top_maps[:5]

                existing = self.account.extra_stats or {}
                existing["steam_cs2"] = {
                    "kills": kills,
                    "deaths": deaths,
                    "kd": round(kills / max(deaths, 1), 2),
                    "matches_played": matches_played,
                    "matches_won": matches_won,
                    "match_winrate": round(matches_won / max(matches_played, 1) * 100, 1),
                    "round_wins": round_wins,
                    "rounds_played": rounds_played,
                    "mvps": m.get("total_mvps", 0),
                    "headshot_pct": round(headshot_kills / max(kills, 1) * 100, 1),
                    "accuracy_pct": round(shots_hit / max(shots_fired, 1) * 100, 1),
                    "hours_played": round(m.get("total_time_played", 0) / 3600, 1),
                    "damage_done": m.get("total_damage_done", 0),
                    "planted_bombs": m.get("total_planted_bombs", 0),
                    "defused_bombs": m.get("total_defused_bombs", 0),
                    "dominations": m.get("total_dominations", 0),
                    "top_weapon": top_weapon,
                    "top_maps": top_maps,
                }
                self.account.extra_stats = existing
                self.account.save(update_fields=["extra_stats"])
        self._auto_link_steam_accounts(games)

    def _sync_opendota(self):
        client = OpenDotaClient()
        wl = client.get_win_loss(self.account.external_id)
        player = client.get_player(self.account.external_id)
        heroes_raw = client.get_heroes(self.account.external_id)
        hero_names = client.get_hero_names()
        item_names = {}
        try:
            item_names = client.get_item_names()
        except Exception:
            pass
        recent_matches = client.get_recent_matches(self.account.external_id, limit=30)

        wins = wl.get("win", 0)
        losses = wl.get("lose", 0)
        total_matches = wins + losses
        winrate = round(wins / total_matches * 100, 1) if total_matches else 0

        top_heroes = sorted(heroes_raw, key=lambda h: h.get("games", 0), reverse=True)[:5]
        top_heroes_data = [
            {"name": hero_names.get(h["hero_id"], f"Hero {h['hero_id']}"), "games": h.get("games", 0),
            "winrate": round(h["win"] / h["games"] * 100, 1) if h.get("games") else 0}
            for h in top_heroes if h.get("games", 0) > 0
        ]

        # параллельно тянем детали всех матчей разом, вместо по одному
        details_by_match = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(client.get_match_details, m["match_id"]): m["match_id"] for m in recent_matches}
            try:
                for future in as_completed(futures, timeout=25):
                    match_id = futures[future]
                    try:
                        details_by_match[match_id] = future.result(timeout=8)
                    except Exception:
                        details_by_match[match_id] = None
            except TimeoutError:
                # общий таймаут вышел раньше, чем все успели — для недошедших просто ставим None,
                # а не роняем всю синхронизацию из-за пары медленных матчей
                for match_id in futures.values():
                    if match_id not in details_by_match:
                        details_by_match[match_id] = None

        role_labels = {1: "Safe Lane (Carry)", 2: "Mid Lane", 3: "Off Lane", 4: "Jungle"}
        role_counter, gpm_list, xpm_list = {}, [], []
        match_history = []

        for m in recent_matches:
            is_radiant = m.get("player_slot", 0) < 128
            won = (is_radiant and m.get("radiant_win")) or (not is_radiant and not m.get("radiant_win"))
            hero = hero_names.get(m.get("hero_id"), "?")
            kda = f"{m.get('kills', 0)}/{m.get('deaths', 0)}/{m.get('assists', 0)}"

            role_key = None
            gpm = xpm = cs = hero_damage = None
            participants = []
            items = []
            verdict = None
            solo = None

            detail = details_by_match.get(m["match_id"])
            if detail:
                try:
                    my_slot = next(p for p in detail.get("players", []) if p.get("player_slot") == m.get("player_slot"))
                    role_key = "Roaming Support" if my_slot.get("is_roaming") else role_labels.get(my_slot.get("lane_role"))
                    if role_key:
                        role_counter[role_key] = role_counter.get(role_key, 0) + 1
                    gpm = my_slot.get("gold_per_min")
                    xpm = my_slot.get("xp_per_min")
                    if gpm is not None: gpm_list.append(gpm)
                    if xpm is not None: xpm_list.append(xpm)
                    cs = (my_slot.get("last_hits") or 0) + (my_slot.get("denies") or 0)
                    hero_damage = my_slot.get("hero_damage")
                    solo = my_slot.get("party_size") == 1

                    participants = [
                        {"account_id": p.get("account_id"), "hero": hero_names.get(p.get("hero_id"), "?"), "is_radiant": p.get("player_slot", 0) < 128}
                        for p in detail.get("players", []) if p.get("account_id")
                    ]

                    items = _extract_items_with_timing(my_slot, item_names)
                    verdict = _compute_match_verdict(my_slot, won)
                except Exception:
                    pass

            played_at = None
            if m.get("start_time"):
                played_at = datetime.fromtimestamp(m["start_time"]).strftime("%d.%m.%Y")

            match_history.append({
                "won": won, "title": hero, "subtitle": kda,
                "match_id": m["match_id"],
                "duration": f"{round(m.get('duration', 0) / 60)} мин",
                "played_at": played_at,
                "participants": participants,
                "items": items,
                "verdict": verdict,
                "solo": solo,
                "details": [
                    {"label": "GPM", "value": gpm if gpm is not None else "—"},
                    {"label": "XPM", "value": xpm if xpm is not None else "—"},
                    {"label": "CS", "value": cs if cs is not None else "—"},
                    {"label": "Урон герою", "value": hero_damage if hero_damage is not None else "—"},
                    {"label": "Роль", "value": role_key or "Неизвестна"},
                ],
            })

        primary_role = max(role_counter, key=role_counter.get) if role_counter else None
        avg_gpm = round(sum(gpm_list) / len(gpm_list)) if gpm_list else None
        avg_xpm = round(sum(xpm_list) / len(xpm_list)) if xpm_list else None
        mmr_estimate = player.get("mmr_estimate", {}).get("estimate")

        self.account.extra_stats = {
            "total_matches": total_matches, "wins": wins, "losses": losses, "winrate": winrate,
            "top_heroes": top_heroes_data, "mmr_estimate": mmr_estimate, "rank_tier": player.get("rank_tier"),
            "primary_role": primary_role, "avg_gpm": avg_gpm, "avg_xpm": avg_xpm,
            "match_history": match_history,
        }
        self.account.skill_rating = mmr_estimate
        self.account.game_label = "Dota 2"
        self.account.save(update_fields=["extra_stats", "skill_rating", "game_label"])


    def _sync_faceit(self):
        from .integrations.faceit_client import FaceitClient, FaceitError

        raw = (self.account.external_id or "").strip()
        if not raw:
            raise SyncError("Укажи ник Faceit или player_id")

        client = FaceitClient()

        try:
            if len(raw) >= 32 and "-" in raw:
                player = client.get_player(raw)
            else:
                player = client.get_player_by_nickname(raw)
        except FaceitError as e:
            raise SyncError(str(e))
        except Exception as e:
            raise SyncError(f"Faceit: не удалось найти игрока ({e})")

        player_id = player.get("player_id")
        if not player_id:
            raise SyncError("Faceit: нет player_id")

        nickname = player.get("nickname") or raw
        games = player.get("games") or {}

        game_id = "cs2"
        game_info = games.get("cs2") or {}
        if not game_info:
            game_id = "csgo"
            game_info = games.get("csgo") or {}

        skill_level = game_info.get("skill_level")
        faceit_elo = game_info.get("faceit_elo")
        try:
            skill_level = int(skill_level) if skill_level is not None else None
        except (TypeError, ValueError):
            skill_level = None
        try:
            faceit_elo = int(faceit_elo) if faceit_elo is not None else None
        except (TypeError, ValueError):
            faceit_elo = None

        def _to_int(v, default=0):
            try:
                return int(float(str(v).replace(",", ".")))
            except (TypeError, ValueError):
                return default

        def _to_float(v, default=None):
            if v is None or v == "":
                return default
            try:
                return float(str(v).replace(",", "."))
            except (TypeError, ValueError):
                return default

        lifetime = {}
        top_maps = []
        matches_total = wins = 0
        winrate = kd = hs = None
        adr = entry_rate = kr = None

        try:
            stats_payload = client.get_player_stats(player_id, game_id)
            lifetime = stats_payload.get("lifetime") or {}
            segments = stats_payload.get("segments") or []

            def L(*keys, default=None):
                for k in keys:
                    if k in lifetime and lifetime[k] not in (None, ""):
                        return lifetime[k]
                return default

            matches_total = _to_int(L("Matches", "matches", default=0))
            wins = _to_int(L("Wins", "wins", default=0))
            wr_raw = L("Win Rate %", "Winrate %", "winrate")
            kd_raw = L("Average K/D Ratio", "K/D Ratio", "K/D", "kd")
            hs_raw = L("Average Headshots %", "Headshots %", "HS %")

            winrate = _to_float(wr_raw)
            if winrate is None and matches_total:
                winrate = round(wins / matches_total * 100, 1)
            elif winrate is not None:
                winrate = round(winrate, 1)
            else:
                winrate = 0

            kd = _to_float(kd_raw, None)
            if kd is not None:
                kd = round(kd, 2)

            hs = _to_float(hs_raw, None)
            if hs is not None:
                hs = round(hs, 1)

            adr = _to_float(L("ADR", "Average Damage per Round", "Damage/Round"))
            if adr is not None:
                adr = round(adr, 1)
            entry_rate = _to_float(L("Entry Success Rate", "Entry Rate %"))
            if entry_rate is not None:
                entry_rate = round(entry_rate, 1)
            kr = _to_float(L("K/R Ratio", "Average K/R Ratio", "Kills/Round"))
            if kr is not None:
                kr = round(kr, 2)

            map_rows = []
            for seg in segments:
                label = (seg.get("label") or "").strip()
                st = seg.get("stats") or {}
                is_map = (
                    (seg.get("type") or "").lower() == "map"
                    or label.lower().startswith("de_")
                    or label.lower().startswith("cs_")
                )
                if not is_map or not label:
                    continue
                m_matches = _to_int(st.get("Matches") or st.get("matches") or 0)
                if m_matches <= 0:
                    continue
                m_wins = _to_int(st.get("Wins") or st.get("wins") or 0)
                m_wr = _to_float(st.get("Win Rate %") or st.get("Winrate %"))
                if m_wr is None:
                    m_wr = round(m_wins / m_matches * 100, 1) if m_matches else 0
                else:
                    m_wr = round(m_wr, 1)
                m_kd = _to_float(st.get("Average K/D Ratio") or st.get("K/D Ratio") or st.get("K/D"))
                if m_kd is not None:
                    m_kd = round(m_kd, 2)
                map_rows.append({
                    "name": label,
                    "matches": m_matches,
                    "winrate": m_wr,
                    "kd": m_kd,
                })
            map_rows.sort(key=lambda x: x["matches"], reverse=True)
            top_maps = map_rows[:8]
        except FaceitError:
            pass
        except Exception:
            pass

        def _sget(stats, *keys, default=None):
            for k in keys:
                if k in stats and stats[k] not in (None, ""):
                    return stats[k]
            return default

        match_history = []
        items = []
        try:
            recent = client.get_recent_match_stats(player_id, game_id, limit=20)
            items = recent.get("items") or []
        except Exception:
            items = []

        if not items:
            try:
                hist = client.get_history(player_id, game=game_id, limit=20)
                items = hist.get("items") or []
            except Exception:
                items = []

        for item in items[:20]:
            stats = item.get("stats") or {}

            match_id = (
                item.get("match_id")
                or item.get("matchId")
                or _sget(stats, "Match Id", "match_id", "Match ID")
                or item.get("id")
            )
            if match_id is not None:
                match_id = str(match_id).strip() or None

            result = _sget(stats, "Result", "result", "Game Result") or item.get("result")
            won = None
            if str(result) in ("1", "Win", "win", "W"):
                won = True
            elif str(result) in ("0", "Loss", "loss", "L"):
                won = False

            kills = _sget(stats, "Kills", "kills") or "0"
            deaths = _sget(stats, "Deaths", "deaths") or "0"
            assists = _sget(stats, "Assists", "assists") or "0"
            kd_m = _sget(stats, "K/D Ratio", "K/D", "kd")
            hs_m = _sget(stats, "Headshots %", "HS %", "Headshots")
            map_name = (
                _sget(stats, "Map", "map")
                or item.get("map")
                or (item.get("game_id") or game_id).upper()
            )
            score = _sget(stats, "Score", "score")
            if not score and item.get("results"):
                sc = (item.get("results") or {}).get("score") or {}
                if sc:
                    score = f"{sc.get('faction1', '?')} / {sc.get('faction2', '?')}"

            played_at = None
            date_raw = (
                item.get("date")
                or item.get("finished_at")
                or item.get("started_at")
                or _sget(stats, "Date")
            )
            if date_raw:
                try:
                    ts = int(date_raw)
                    if ts > 10_000_000_000:
                        ts //= 1000
                    played_at = datetime.utcfromtimestamp(ts).strftime("%d.%m.%Y")
                except Exception:
                    played_at = str(date_raw)[:10]

            verdict = None
            try:
                kd_f = float(str(kd_m).replace(",", "."))
                if kd_f >= 1.4:
                    verdict = {"label": "Great", "tone": "great"}
                elif kd_f >= 1.1:
                    verdict = {"label": "Good", "tone": "good"}
                elif kd_f >= 0.85:
                    verdict = {"label": "OK", "tone": "neutral"}
                elif kd_f >= 0.6:
                    verdict = {"label": "Bad", "tone": "bad"}
                else:
                    verdict = {"label": "Rough", "tone": "terrible"}
            except Exception:
                verdict = None

            elo_raw = (
                _sget(stats, "Elo", "ELO", "Rating", "Elo Change", "elo_change")
                or item.get("elo")
                or item.get("elo_change")
            )
            elo_change = None
            if elo_raw is not None and str(elo_raw).strip() != "":
                try:
                    elo_change = int(float(str(elo_raw).replace(",", ".").replace("+", "")))
                except (TypeError, ValueError):
                    elo_change = None

            details = [
                {"label": "Счёт", "value": score or "—"},
                {"label": "K/D", "value": kd_m or "—"},
                {"label": "HS %", "value": hs_m or "—"},
                {"label": "Карта", "value": map_name},
            ]
            elo_sub = ""
            if elo_change is not None:
                sign = "+" if elo_change > 0 else ""
                details.insert(0, {"label": "ELO", "value": f"{sign}{elo_change}"})
                elo_sub = f" · {sign}{elo_change} ELO"

            match_history.append({
                "won": won,
                "title": map_name,
                "subtitle": f"{kills}/{deaths}/{assists}"
                    + (f" · KD {kd_m}" if kd_m else "")
                    + elo_sub,
                "duration": None,
                "match_id": match_id,
                "played_at": played_at,
                "verdict": verdict,
                "elo_change": elo_change,
                "solo": None,
                "details": details,
            })

        form = []
        for m in match_history[:10]:
            if m["won"] is True:
                form.append("W")
            elif m["won"] is False:
                form.append("L")

        # avg за последние матчи — считаем сами
        n = 0
        sum_k = sum_d = sum_a = 0
        sum_hs = 0
        hs_n = 0
        for m in match_history[:20]:
            parts = (m.get("subtitle") or "").split("·")[0].strip().split("/")
            if len(parts) >= 3:
                sum_k += _to_int(parts[0])
                sum_d += _to_int(parts[1])
                sum_a += _to_int(parts[2])
                n += 1
            for det in m.get("details") or []:
                if det.get("label") in ("HS %", "HS"):
                    hv = _to_float(det.get("value"))
                    if hv is not None:
                        sum_hs += hv
                        hs_n += 1

        avg_kills = round(sum_k / n, 1) if n else None
        avg_deaths = round(sum_d / n, 1) if n else None
        avg_assists = round(sum_a / n, 1) if n else None
        avg_kd = round((sum_k + sum_a) / max(sum_d, 1), 2) if n else None
        avg_hs = round(sum_hs / hs_n, 1) if hs_n else hs

        self.account.extra_stats = {
            "player_id": player_id,
            "game_id": game_id,
            "skill_level": skill_level,
            "faceit_elo": faceit_elo,
            "matches": matches_total,
            "wins": wins,
            "winrate": winrate,
            "kd": kd,
            "hs_percent": hs,
            "avg_kills": avg_kills,
            "avg_deaths": avg_deaths,
            "avg_assists": avg_assists,
            "avg_kd_recent": avg_kd,
            "avg_hs_recent": avg_hs,
            "adr": adr,
            "entry_success": entry_rate,
            "kr": kr,
            "sample_size": n,
            "lifetime": lifetime,
            "top_maps": top_maps,
            "recent_form": form,
            "match_history": match_history,
            "country": player.get("country"),
            "avatar": player.get("avatar"),
        }
        self.account.game_label = f"Faceit {game_id.upper()}"
        self.account.nickname = nickname
        if faceit_elo is not None:
            self.account.skill_rating = faceit_elo
        if player.get("avatar"):
            self.account.avatar = player.get("avatar")

        self.account.save(update_fields=[
            "extra_stats", "game_label", "nickname", "skill_rating", "avatar",
        ])
        
    def _sync_roblox(self):
        from datetime import datetime
        from .integrations.roblox_client import RobloxClient
        client = RobloxClient()
        user = client.get_user_by_username(self.account.external_id)
        user_id = user["id"]
        details = client.get_user_details(user_id)
        friends = client.get_friends_count(user_id)
        followers = client.get_followers_count(user_id)

        account_age_days = None
        created = details.get("created")
        if created:
            created_date = datetime.fromisoformat(created.replace("Z", "+00:00"))
            account_age_days = (timezone.now() - created_date).days

        self.account.extra_stats = {
            "display_name": details.get("displayName"),
            "account_age_days": account_age_days,
            "friends_count": friends,
            "followers_count": followers,
            "has_verified_badge": details.get("hasVerifiedBadge", False),
        }
        self.account.game_label = "Roblox"
        self.account.nickname = user.get("name", "")
        self.account.verified = True
        self.account.save(update_fields=["extra_stats", "game_label", "nickname", "verified"])


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

def get_steam_library(game_account: GameAccount):
    """Один ряд на appid: часы всего + часы сегодня (дельта с вчера)."""
    today = date.today()
    yesterday = today - timedelta(days=1)

    snaps = list(
        DailySnapshot.objects
        .filter(game_account=game_account)
        .order_by("appid", "-date")
    )

    latest_by_app = {}
    by_app_date = {}
    for s in snaps:
        by_app_date[(s.appid, s.date)] = s
        if s.appid not in latest_by_app:
            latest_by_app[s.appid] = s

    result = []
    for appid, latest in latest_by_app.items():
        hours_total = round((latest.playtime_forever or 0) / 60, 1)

        today_s = by_app_date.get((appid, today))
        yest_s = by_app_date.get((appid, yesterday))
        hours_today = None
        if today_s and yest_s:
            hours_today = round(
                max((today_s.playtime_forever or 0) - (yest_s.playtime_forever or 0), 0) / 60,
                1,
            )

        result.append({
            "appid": appid,
            "name": latest.game_name,
            "hours_total": hours_total,
            "hours_today": hours_today,  # None → на UI "—"
        })

    result.sort(key=lambda x: x["hours_total"], reverse=True)
    return result

def get_account_summary(game_account: GameAccount):
    if game_account.platform == "steam":
        library = get_steam_library(game_account)
        total_hours = sum(g["hours_total"] for g in library)
        most = library[0]["name"] if library else None
        return {
            "total_playtime": int(total_hours * 60),  # минуты, как раньше
            "most_played_game": most,
            "games_count": len(library),
            "library": library,
        }

    snapshots = game_account.snapshots.all()
    if not snapshots:
        return {"total_playtime": 0, "most_played_game": None, "games_count": 0, "library": []}

    # для не-steam — latest per appid
    latest = {}
    for s in snapshots.order_by("-date"):
        if s.appid not in latest:
            latest[s.appid] = s
    total = sum(s.playtime_forever for s in latest.values())
    most_played = max(latest.values(), key=lambda s: s.playtime_forever) if latest else None
    return {
        "total_playtime": total,
        "most_played_game": most_played.game_name if most_played else None,
        "games_count": len(latest),
        "library": [],
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
            "tags": [t for t in [
                {"label": extra_stats.get("primary_role"), "tone": "accent"} if extra_stats.get("primary_role") else None,
                {"label": f"GPM {extra_stats['avg_gpm']}"} if extra_stats.get("avg_gpm") else None,
                {"label": f"XPM {extra_stats['avg_xpm']}"} if extra_stats.get("avg_xpm") else None,
            ] if t],
            "list_title": "Любимые герои",
            "list": [{"name": h["name"], "sub": f"{h['games']} игр", "value": f"{h['winrate']}%", "good": h["winrate"] >= 50} for h in extra_stats.get("top_heroes", [])],
            "match_history": extra_stats.get("match_history", []),
        }

    if platform == "fortnite":
        return {
            "game_label": "Fortnite",
            "kind": "fortnite_panel",  # фронт рисует FortniteStatsPanel
            "windows": extra_stats.get("windows") or {},
            "default_window": extra_stats.get("default_window") or "lifetime",
            "pr": extra_stats.get("pr"),
            "earnings": extra_stats.get("earnings"),
            "bp_level": extra_stats.get("bp_level"),
            "bp_progress": extra_stats.get("bp_progress"),
            "metrics": [
                {"label": "побед", "value": extra_stats.get("wins", 0), "tone": "win"},
                {"label": "матчей", "value": extra_stats.get("matches", 0)},
                {"label": "винрейт", "value": f"{extra_stats.get('winrate', 0)}%", "tone": "accent"},
                {"label": "K/D", "value": extra_stats.get("kd", 0)},
            ],
            "badge": f"BP {extra_stats['bp_level']}" if extra_stats.get("bp_level") is not None else None,
            "tags": [],
            "list": [],
            "match_history": [],
        }
    
    if platform == "deadlock":
        matches = extra_stats.get("matches") or 0
        wins = extra_stats.get("wins") or 0
        losses = extra_stats.get("losses")
        if losses is None and matches:
            losses = max(matches - wins, 0)
        wr = extra_stats.get("winrate")
        badge = extra_stats.get("badge")
        tier = extra_stats.get("tier") or (
            f"Badge {badge}" if badge else "Unranked"
        )
        top_heroes = extra_stats.get("top_heroes") or []
        form = extra_stats.get("recent_form") or []
        avg_kda = extra_stats.get("avg_kda")
        avg_nw = extra_stats.get("avg_net_worth")
        hours = extra_stats.get("hours_played")

        metrics = [
            {"label": "матчей", "value": matches},
            {"label": "побед", "value": wins, "tone": "win"},
            {
                "label": "пораж.",
                "value": losses if losses is not None else "—",
                "tone": "loss",
            },
            {
                "label": "винрейт",
                "value": f"{wr}%" if wr is not None else "—",
                "tone": "accent",
            },
        ]
        if avg_nw is not None:
            metrics.append({"label": "ср. NW", "value": avg_nw})
        if hours is not None:
            metrics.append({"label": "часов", "value": hours})

        tags = []
        if avg_kda:
            tags.append({"label": f"KDA {avg_kda}"})
        if form:
            tags.append({"label": "Форма " + "".join(str(x) for x in form[:10])})

        return {
            "game_label": "Deadlock",
            "metrics": metrics[:8],
            "badge": tier,
            "tags": tags,
            "list_title": "Любимые герои" if top_heroes else "",
            "list": [
                {
                    "name": h.get("name") or "?",
                    "sub": f"{h.get('games', 0)} игр",
                    "value": str(h.get("games", 0)),
                    "good": True,
                }
                for h in top_heroes
            ],
            "list_title_2": "Сводка",
            "list_2": [
                {"name": "Rank / tier", "value": tier},
                {"name": "Badge", "value": badge if badge is not None else "—"},
                {"name": "Ср. K/D/A", "value": avg_kda or "—"},
                {
                    "name": "Ср. net worth",
                    "value": avg_nw if avg_nw is not None else "—",
                },
            ],
            "match_history": extra_stats.get("match_history") or [],
        }

    if platform == "lol":
        form = extra_stats.get("recent_form") or []
        form_str = "".join(form[:12]) if form else None
        top = extra_stats.get("top_champions") or []
        hist = extra_stats.get("match_history") or []
        wins_h = sum(1 for m in hist if m.get("won"))
        wr_recent = round(wins_h / len(hist) * 100, 1) if hist else None

        metrics = [
            {"label": "solo W", "value": extra_stats.get("wins", 0), "tone": "win"},
            {"label": "solo L", "value": extra_stats.get("losses", 0), "tone": "loss"},
            {"label": "винрейт", "value": f"{extra_stats.get('winrate', 0)}%", "tone": "accent"},
            {"label": "LP", "value": extra_stats.get("lp") if extra_stats.get("lp") is not None else "—"},
        ]
        if extra_stats.get("avg_kda"):
            metrics.append({"label": "ср. KDA", "value": extra_stats["avg_kda"].split(" ")[0], "tone": "accent"})
        if wr_recent is not None:
            metrics.append({"label": "форма", "value": f"{wr_recent}%", "tone": "accent"})

        return {
            "game_label": "League of Legends",
            "metrics": metrics[:6],
            "badge": extra_stats.get("tier") or "Unranked",
            "tags": [t for t in [
                {"label": f"KDA {extra_stats['avg_kda']}"} if extra_stats.get("avg_kda") else None,
                {"label": f"Main {extra_stats['main_agent']}"} if extra_stats.get("main_agent") else None,
                {"label": f"Flex {extra_stats['flex_tier']} ({extra_stats.get('flex_lp') or 0} LP)"} if extra_stats.get("flex_tier") else None,
                {"label": f"Матчей в истории {len(hist)}"},
                {"label": f"Форма {form_str}"} if form_str else None,
            ] if t],
            "list_title": "Топ чемпионы (последние игры)",
            "list": [
                {"name": c["name"], "sub": f"{c['games']} игр в выборке", "value": str(c["games"]), "good": c["games"] >= 3}
                for c in top
            ],
            "list_title_2": "Ранкед",
            "list_2": [
                {"name": "Solo/Duo", "sub": f"{extra_stats.get('wins', 0)}W / {extra_stats.get('losses', 0)}L",
                 "value": f"{extra_stats.get('tier') or '—'} · {extra_stats.get('lp') or 0} LP"},
                {"name": "Flex", "sub": f"{extra_stats.get('flex_wins') or 0}W / {extra_stats.get('flex_losses') or 0}L",
                 "value": f"{extra_stats.get('flex_tier') or '—'} · {extra_stats.get('flex_lp') or 0} LP"},
                {"name": "Регион", "sub": "", "value": (extra_stats.get("riot_platform") or "euw1").upper()},
            ],
            "match_history": hist,
        }

    if platform == "valorant":
        metrics = [
            {"label": "матчей", "value": extra_stats.get("matches", 0)},
            {"label": "побед", "value": extra_stats.get("wins", 0), "tone": "win"},
            {
                "label": "винрейт",
                "value": f"{extra_stats.get('winrate', 0)}%",
                "tone": "accent",
            },
            {"label": "RR", "value": extra_stats.get("rr", 0)},
        ]
        sample = extra_stats.get("sample_size") or 0
        if extra_stats.get("avg_kills") is not None:
            metrics.append({
                "label": f"ср. килы ({sample})",
                "value": extra_stats["avg_kills"],
                "tone": "accent",
            })
        if extra_stats.get("avg_acs") is not None:
            metrics.append({
                "label": "ср. ACS",
                "value": extra_stats["avg_acs"],
                "tone": "accent",
            })
        if extra_stats.get("avg_kd_recent") is not None:
            metrics.append({
                "label": "K/D (выборка)",
                "value": extra_stats["avg_kd_recent"],
            })

        tags = []
        if extra_stats.get("main_agent"):
            tags.append({"label": extra_stats["main_agent"]})
        if extra_stats.get("avg_deaths") is not None:
            tags.append({
                "label": (
                    f"ср. {extra_stats.get('avg_kills')}/"
                    f"{extra_stats.get('avg_deaths')}/"
                    f"{extra_stats.get('avg_assists') or 0}"
                )
            })

        return {
            "game_label": "Valorant",
            "metrics": metrics[:8],
            "badge": extra_stats.get("tier"),
            "tags": tags,
            "list_title": "",
            "list": [],
            "match_history": extra_stats.get("match_history", []),
        }

    if platform == "pubg":
        status_map = {
            0: "Offline", 1: "Online", 2: "Busy", 3: "Away",
            4: "Snooze", 5: "Trade", 6: "Looking to play",
        }
        st = status_map.get(extra_stats.get("steam_status"), "—")
        h = extra_stats.get("hours_played") or 0
        h2 = extra_stats.get("hours_2weeks") or 0
        return {
            "game_label": "PUBG",
            "metrics": [
                {"label": "часов", "value": h, "tone": "accent"},
                {"label": "2 недели", "value": h2},
                {"label": "минут", "value": extra_stats.get("minutes_forever") or int(h * 60)},
            ],
            "badge": "Steam · limited",
            "tags": [t for t in [
                {"label": st},
                {"label": extra_stats["steam_country"]} if extra_stats.get("steam_country") else None,
                {"label": "Нет BR API — только playtime"},
            ] if t],
            "list_title": "Почему мало цифр",
            "list": [
                {
                    "name": "Источник",
                    "sub": "Steam GetOwnedGames (app 578080)",
                    "value": f"{h} ч",
                    "good": True,
                },
                {
                    "name": "Недоступно без PUBG API",
                    "sub": "wins, K/D, damage, seasons, matches",
                    "value": "—",
                    "good": False,
                },
            ],
            "list_title_2": "Профиль",
            "list_2": [
                {"name": "Статус Steam", "sub": "", "value": st},
                {"name": "Страна", "sub": "", "value": extra_stats.get("steam_country") or "—"},
                {"name": "За 14 дней", "sub": "", "value": f"{h2} ч"},
            ],
            "match_history": [],
        }

    if platform == "roblox":
        return {
            "game_label": "Roblox",
            "metrics": [
                {"label": "друзей", "value": extra_stats.get("friends_count", 0)},
                {"label": "подписчиков", "value": extra_stats.get("followers_count", 0)},
                {"label": "дней в Roblox", "value": extra_stats.get("account_age_days") or "—"},
            ],
            "badge": "✓ Verified" if extra_stats.get("has_verified_badge") else None,
            "tags": [{"label": "Публичной игровой статистики Roblox не предоставляет"}],
            "list_title": "Профиль",
            "list": [{"name": "Отображаемое имя", "sub": "", "value": extra_stats.get("display_name", "—")}],
            "match_history": [],
        }

    if platform == "steam":
        cs2 = extra_stats.get("steam_cs2")
        if not cs2:
            return None
        return {
            "game_label": "CS2 (Steam)",
            "metrics": [
                {"label": "матчей", "value": cs2.get("matches_played", 0)},
                {"label": "побед", "value": cs2.get("matches_won", 0), "tone": "win"},
                {"label": "винрейт", "value": f"{cs2.get('match_winrate', 0)}%", "tone": "accent"},
                {"label": "K/D", "value": cs2.get("kd", 0)},
            ],
            "badge": None,
            "tags": [t for t in [
                {"label": f"HS {cs2['headshot_pct']}%"} if cs2.get("headshot_pct") else None,
                {"label": f"Точность {cs2['accuracy_pct']}%"} if cs2.get("accuracy_pct") else None,
                {"label": f"Любимое оружие: {cs2['top_weapon']['name']}"} if cs2.get("top_weapon") else None,
            ] if t],
            "list_title": "Топ карты",
            "list": [
                {"name": mp["name"], "sub": f"{mp['rounds']} раундов", "value": f"{mp['winrate']}%", "good": mp["winrate"] >= 50}
                for mp in cs2.get("top_maps", [])
            ],
            "list_title_2": "Дополнительно",
            "list_2": [
                {"name": "MVP", "sub": "", "value": cs2.get("mvps", 0)},
                {"name": "Наиграно часов", "sub": "", "value": cs2.get("hours_played", 0)},
                {"name": "Раундов выиграно", "sub": "", "value": cs2.get("round_wins", 0)},
                {"name": "Урон нанесено", "sub": "", "value": cs2.get("damage_done", 0)},
                {"name": "Бомб заложено/обезврежено", "sub": "", "value": f"{cs2.get('planted_bombs', 0)} / {cs2.get('defused_bombs', 0)}"},
            ],
            "match_history": [],
        }