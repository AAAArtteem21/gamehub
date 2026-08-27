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
            elif self.account.platform == "valorant":
                self._sync_valorant()
            elif self.account.platform == "pubg":
                self._sync_pubg()
            elif self.account.platform == "roblox":
                self._sync_roblox()
            elif self.account.platform == "fortnite":
                self._sync_fortnite()
        except requests.Timeout:
            raise ExternalServiceUnavailable("Внешний сервис не отвечает, попробуй позже")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise SyncError("Аккаунт не найден на платформе — проверь ID")
            raise ExternalServiceUnavailable("Ошибка внешнего сервиса, попробуй позже")

        self.account.verified = True
        self.account.last_synced_at = timezone.now()
        self.account.save(update_fields=["verified", "last_synced_at"])


    def _sync_fortnite(self):
        from .integrations.fortnite_client import FortniteClient
        client = FortniteClient()
        profile = client.get_profile(self.account.external_id)

        segments = profile.get("segments", [])
        overview = next((s for s in segments if s.get("type") == "overview"), segments[0] if segments else {})
        stats = overview.get("stats", {})

        kills = stats.get("kills", {}).get("value", 0)
        wins = stats.get("wins", {}).get("value", 0)
        matches = stats.get("matchesPlayed", {}).get("value", 0)
        kd = stats.get("kd", {}).get("value", 0)
        top1_pct = stats.get("winRatio", {}).get("value", 0)
        avg_survival = stats.get("scorePerMatch", {}).get("value", "—")

        self.account.extra_stats = {
            "matches": matches, "wins": wins, "kills": kills, "kd": kd,
            "winrate": top1_pct, "avg_score": avg_survival,
        }
        self.account.game_label = "Fortnite"
        self.account.save(update_fields=["extra_stats", "game_label"])

    def _sync_lol(self):
        from .integrations.riot_client import RiotClient
        client = RiotClient()
        game_name, tag_line = self.account.external_id.split("#")
        account = client.get_account_by_riot_id(game_name, tag_line)
        puuid = account["puuid"]
        summoner = client.get_summoner_by_puuid(puuid)
        ranked = client.get_ranked_stats(summoner["id"])
        solo_queue = next((r for r in ranked if r.get("queueType") == "RANKED_SOLO_5x5"), None)

        match_ids = client.get_match_history(puuid, count=10)
        match_history = []
        for match_id in match_ids[:10]:
            try:
                match = client.get_match_details(match_id)
                p = next(x for x in match["info"]["participants"] if x["puuid"] == puuid)
                cs = p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0)
                match_history.append({
                    "won": p["win"], "title": p["championName"],
                    "subtitle": f"{p['kills']}/{p['deaths']}/{p['assists']}",
                    "duration": f"{round(match['info'].get('gameDuration', 0) / 60)} мин",
                    "played_at": datetime.fromtimestamp(match["info"].get("gameCreation", 0) / 1000).strftime("%d.%m.%Y") if match["info"].get("gameCreation") else None,
                    "details": [
                        {"label": "CS", "value": cs},
                        {"label": "Золото", "value": p.get("goldEarned", "—")},
                        {"label": "Урон", "value": p.get("totalDamageDealtToChampions", "—")},
                        {"label": "Роль", "value": p.get("teamPosition") or "Неизвестна"},
                    ],
                })
            except Exception:
                continue

        wins = solo_queue.get("wins", 0) if solo_queue else 0
        losses = solo_queue.get("losses", 0) if solo_queue else 0
        total = wins + losses
        winrate = round(wins / total * 100, 1) if total else 0

        self.account.extra_stats = {
            "tier": solo_queue.get("tier") if solo_queue else None,
            "rank": solo_queue.get("rank") if solo_queue else None,
            "lp": solo_queue.get("leaguePoints") if solo_queue else None,
            "wins": wins, "losses": losses, "matches": total, "winrate": winrate,
            "match_history": match_history,
        }
        self.account.game_label = "League of Legends"
        self.account.nickname = f"{game_name}#{tag_line}"
        self.account.save(update_fields=["extra_stats", "game_label", "nickname"])

    def _sync_valorant(self):
        from .integrations.valorant_client import ValorantClient
        client = ValorantClient()
        name, tag = self.account.external_id.split("#")
        account = client.get_account(name, tag)
        region = account.get("region", "eu")
        mmr = client.get_mmr(name, tag, region=region)
        matches = client.get_matches(name, tag, region=region, size=10)

        current_tier = mmr.get("current_data", {}).get("currenttierpatched", "Unranked")
        rr = mmr.get("current_data", {}).get("ranking_in_tier", 0)

        rr_by_match = {}
        try:
            history = client.get_mmr_history(name, tag, region=region)
            for h in history:
                match_id = h.get("match_id")
                if match_id:
                    rr_by_match[match_id] = h.get("mmr_change_to_last_game")
        except Exception:
            pass  

        match_history, agent_counter = [], {}
        for match in matches[:10]:
            players = match.get("players", {}).get("all_players", [])
            me = next((p for p in players if p["name"].lower() == name.lower()), None)
            if not me:
                continue

            team_won = match.get("teams", {}).get(me["team"].lower(), {}).get("has_won", False)
            agent = me.get("character", "?")
            agent_counter[agent] = agent_counter.get(agent, 0) + 1
            stats = me.get("stats", {})
            map_name = match.get("metadata", {}).get("map", "?")
            match_id = match.get("metadata", {}).get("matchid")
            rounds_played = match.get("metadata", {}).get("rounds_played") or 1
            combat_score = stats.get("score", 0)
            acs = round(combat_score / rounds_played)

            details = [
                {"label": "Карта", "value": map_name},
                {"label": "Combat Score (ACS)", "value": acs},
                {"label": "Хедшоты", "value": stats.get("headshots", "—")},
                {"label": "Бодишоты", "value": stats.get("bodyshots", "—")},
            ]
            rr_change = rr_by_match.get(match_id)
            if rr_change is not None:
                details.append({"label": "RR", "value": f"{'+' if rr_change >= 0 else ''}{rr_change}"})

            match_history.append({
                "won": team_won, "title": agent,
                "subtitle": f"{stats.get('kills', 0)}/{stats.get('deaths', 0)}/{stats.get('assists', 0)}",
                "duration": None,
                "right_label": f"{'+' if rr_change is not None and rr_change >= 0 else ''}{rr_change} RR" if rr_change is not None else None,
                "details": details,
            })

        main_agent = max(agent_counter, key=agent_counter.get) if agent_counter else None
        wins = sum(1 for f in match_history if f["won"])
        winrate = round(wins / len(match_history) * 100, 1) if match_history else 0

        self.account.extra_stats = {
            "matches": len(match_history), "wins": wins, "winrate": winrate,
            "tier": current_tier, "rr": rr, "main_agent": main_agent,
            "match_history": match_history,
        }
        self.account.game_label = "Valorant"
        self.account.nickname = f"{name}#{tag}"
        self.account.save(update_fields=["extra_stats", "game_label", "nickname"])

    def _sync_pubg(self):
        from .integrations.pubg_client import PubgClient
        client = PubgClient()

        profile = client.get_profile("steam", self.account.external_id)
        segments = profile.get("segments", [])
        overview = next((s for s in segments if s.get("type") == "overview"), segments[0] if segments else {})
        stats = overview.get("stats", {})

        kills = stats.get("kills", {}).get("value", 0)
        wins = stats.get("wins", {}).get("value", 0)
        matches = stats.get("matchesPlayed", {}).get("value", 0)
        kd = stats.get("kd", {}).get("value", 0)
        winrate = round(wins / max(matches, 1) * 100, 1)

        self.account.extra_stats = {
            "matches": matches, "wins": wins, "kills": kills,
            "kd": kd, "winrate": winrate,
        }
        self.account.game_label = "PUBG"
        self.account.save(update_fields=["extra_stats", "game_label"])


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
        recent_matches = client.get_recent_matches(self.account.external_id, limit=6)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(client.get_match_details, m["match_id"]): m["match_id"] for m in recent_matches}
            for future in as_completed(futures, timeout=25):  # жёсткий потолок ожидания на всю группу
                match_id = futures[future]
                try:
                    details_by_match[match_id] = future.result(timeout=8)  # на каждый отдельный запрос — до 8 сек
                except Exception:
                    details_by_match[match_id] = None

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
        elo = player.get("games", {}).get("cs2", {}).get("faceit_elo")
        skill_level = player.get("games", {}).get("cs2", {}).get("skill_level")

        match_history = []
        for m in matches.get("items", [])[:10]:
            try:
                match_stats = client.get_match_stats(m.get("match_id"))
                round_data = match_stats.get("rounds", [{}])[0]
                round_stats = round_data.get("round_stats", {})
                my_stats, my_team_id = None, None
                for team in round_data.get("teams", []):
                    for p in team.get("players", []):
                        if p.get("player_id") == player["player_id"]:
                            my_stats = p.get("player_stats", {})
                            my_team_id = team.get("team_id")
                won = my_team_id is not None and round_stats.get("Winner") == my_team_id
                if my_stats:
                    match_history.append({
                        "won": won, "title": round_stats.get("Map", "?"),
                        "subtitle": f"{my_stats.get('Kills','0')}/{my_stats.get('Deaths','0')}/{my_stats.get('Assists','0')}",
                        "duration": None,
                        "details": [
                            {"label": "HS%", "value": my_stats.get("Headshots %", "—")},
                            {"label": "K/D", "value": my_stats.get("K/D Ratio", "—")},
                            {"label": "MVP", "value": my_stats.get("MVPs", "—")},
                        ],
                    })
            except Exception:
                continue

        self.account.extra_stats = {
            "matches": match_count, "wins": wins, "winrate": winrate,
            "avg_kd": avg_kd, "avg_headshots": avg_hs,
            "elo": elo, "skill_level": skill_level,
            "match_history": match_history,
        }
        self.account.skill_rating = elo
        self.account.game_label = "CS2"
        self.account.nickname = player.get("nickname", "")
        self.account.avatar = player.get("avatar", "")
        self.account.save(update_fields=["extra_stats", "skill_rating", "game_label", "nickname", "avatar"])
        
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
            "metrics": [
                {"label": "матчей", "value": extra_stats.get("matches", 0)},
                {"label": "побед", "value": extra_stats.get("wins", 0), "tone": "win"},
                {"label": "винрейт", "value": f"{extra_stats.get('winrate', 0)}%", "tone": "accent"},
                {"label": "K/D", "value": extra_stats.get("kd", 0)},
            ],
            "badge": None, "tags": [],
            "list_title": "Дополнительно",
            "list": [
                {"name": "Всего убийств", "sub": "", "value": extra_stats.get("kills", 0)},
                {"name": "Средний счёт за матч", "sub": "", "value": extra_stats.get("avg_score", "—")},
            ],
            "match_history": [],
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
            "tags": [{"label": f"HS {extra_stats.get('avg_headshots', 0)}%"}],
            "list_title": "", "list": [],
            "match_history": extra_stats.get("match_history", []),
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
            "tags": [{"label": f"{extra_stats.get('lp', 0)} LP"}],
            "list_title": "", "list": [],
            "match_history": extra_stats.get("match_history", []),
        }

    if platform == "valorant":
        return {
            "game_label": "Valorant",
            "metrics": [
                {"label": "матчей", "value": extra_stats.get("matches", 0)},
                {"label": "побед", "value": extra_stats.get("wins", 0), "tone": "win"},
                {"label": "винрейт", "value": f"{extra_stats.get('winrate', 0)}%", "tone": "accent"},
                {"label": "RR", "value": extra_stats.get("rr", 0)},
            ],
            "badge": extra_stats.get("tier"),
            "tags": [{"label": extra_stats.get("main_agent")}] if extra_stats.get("main_agent") else [],
            "list_title": "", "list": [],
            "match_history": extra_stats.get("match_history", []),
        }

    if platform == "pubg":
        return {
            "game_label": "PUBG",
            "metrics": [
                {"label": "матчей", "value": extra_stats.get("matches", 0)},
                {"label": "побед", "value": extra_stats.get("wins", 0), "tone": "win"},
                {"label": "винрейт", "value": f"{extra_stats.get('winrate', 0)}%", "tone": "accent"},
                {"label": "K/D", "value": extra_stats.get("kd", 0)},
            ],
            "badge": None, "tags": [],
            "list_title": "Статистика",
            "list": [{"name": "Всего убийств", "sub": "", "value": extra_stats.get("kills", 0)}],
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