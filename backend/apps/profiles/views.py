from django.shortcuts import render
from django.core.cache import cache
from rest_framework import viewsets,permissions,status 
from rest_framework.decorators import action 
from rest_framework.response import Response 
from rest_framework.views import APIView
import threading
from django.core.cache import cache

from .models import GameAccount
from .serializers import GameAccountSerializer
from .serivces import ProfileSyncService,SyncError,get_account_summary
from .tasks import sync_single_account

SYNC_COOLDOWN_SECONDS =300
LIST_CACHE_TIMEOUT = 120
MAX_ACCOUNTS_PER_PLATFORM = 1

def _list_cache_key(user_id):
    return f'game_accounts:{user_id}'

def _run_sync_in_background(account_id):
    from .models import GameAccount
    try:
        account = GameAccount.objects.get(id=account_id)
        ProfileSyncService(account).sync()
        cache.set(f"sync_status:{account_id}", {"status": "done"}, timeout=300)
    except Exception as e:
        cache.set(f"sync_status:{account_id}", {"status": "error", "detail": str(e)}, timeout=300)
    finally:
        cache.delete(f"profile_sync_cooldown:{account_id}")


class GameAccountViewSet(viewsets.ModelViewSet):
    serializer_class = GameAccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (GameAccount.objects.filter(user=self.request.user).prefetch_related('snapshots').order_by('-created_at'))
    
    def list(self, request, *args, **kwargs):
        cache_key = _list_cache_key(request.user.id)

        cached = cache.get(cache_key)

        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)

        cache.set(
            cache_key,
            response.data,
            timeout=LIST_CACHE_TIMEOUT
        )

        return response
        
    def create(self,request,*args,**kwargs):
        platform = request.data.get('platform')
        existing_count = GameAccount.objects.filter(
            user=request.user,platform=platform
        ).count()
        if existing_count >= MAX_ACCOUNTS_PER_PLATFORM:
            return Response (
                {'detail': f'Уже подключен аккаунт для платформы{platform}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        response = super().create(request,*args,**kwargs)
        cache.delete(_list_cache_key(request.user.id))
        return response
    
    def destroy(self, request, *args, **kwargs):
        response = super().destroy(request,*args,**kwargs)
        cache.delete(_list_cache_key(request.user.id))
        return response 
    
    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        account = self.get_object()
        cooldown_key = f"profile_sync_cooldown:{account.id}"

        if cache.get(cooldown_key):
            return Response(
                {"detail": "Синхронизация уже запущена, подожди немного"},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        cache.set(cooldown_key, True, timeout=300)
        cache.set(f"sync_status:{account.id}", {"status": "syncing"}, timeout=300)

        thread = threading.Thread(target=_run_sync_in_background, args=(account.id,), daemon=True)
        thread.start()

        return Response({"detail": "Синхронизация запущена"}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=["get"])
    def sync_status(self, request, pk=None):
        account = self.get_object()
        status_data = cache.get(f"sync_status:{account.id}", {"status": "idle"})
        if status_data.get("status") == "done":
            return Response({**status_data, "account": self.get_serializer(account).data})
        return Response(status_data)
    
    @action(detail=True,methods=['get'])
    def summary(self,request,pk=None):
        account = self.get_object()
        return Response(get_account_summary(account))
    
class LeaderboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        game = request.query_params.get("game")
        qs = GameAccount.objects.filter(verified=True).exclude(extra_stats__isnull=True).select_related("user")
        if game:
            qs = qs.filter(game_label__iexact=game)

        accounts = list(qs)

        def sort_key(acc):
            stats = acc.extra_stats or {}
            return acc.skill_rating or stats.get("total_matches", 0) or stats.get("matches", 0) or 0

        accounts.sort(key=sort_key, reverse=True)
        accounts = accounts[:10]

        data = []
        for acc in accounts:
            stats = acc.extra_stats or {}
            matches = stats.get("total_matches") or stats.get("matches") or 0
            winrate = stats.get("winrate", 0)
            data.append({
                "user_id": acc.user.id,
                "username": acc.user.username,
                "platform": acc.platform,
                "skill_rating": acc.skill_rating,
                "matches": matches,
                "winrate": winrate,
            })
        return Response(data)
class PublicProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        from django.contrib.auth import get_user_model
        from apps.users.models import ProfileView as ProfileViewModel

        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Игрок не найден"}, status=404)

        views_count = ProfileViewModel.objects.filter(viewed_user=user).count()
        if request.user.is_authenticated and request.user.id != user.id:
            ProfileViewModel.objects.create(viewer=request.user, viewed_user=user)
            views_count += 1

        accounts = GameAccount.objects.filter(user=user).prefetch_related("snapshots")

        accounts_data = []
        for acc in accounts:
            try:
                serialized = GameAccountSerializer(acc, context={"request": request}).data
                accounts_data.append(serialized)
            except Exception as e:
                # не роняем весь профиль из-за одного проблемного аккаунта —
                # пропускаем его, но остальные данные юзер всё равно увидит
                continue

        profile = getattr(user, "profile", None)

        return Response({
            "username": user.username,
            "display_name": profile.display_name if profile else user.username,
            "avatar_url": profile.avatar_url if profile else None,
            "views_count": views_count,
            "accounts": accounts_data,
        })

class WorldLeaderboardView(APIView):
    """
    GET /api/world-leaderboard/?game=dota2|lol — топ игроков из открытых источников,
    включая тех, кто никогда не регистрировался на GameHub
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        game = request.query_params.get("game", "dota2")

        if game == "dota2":
            from .integrations.opendota_client import OpenDotaClient, OpenDotaError
            cached = cache.get("world_leaderboard_dota2")
            if cached:
                return Response(cached)
            client = OpenDotaClient()
            try:
                players = client.get_pro_players()[:15]
            except OpenDotaError as e:
                return Response({"detail": str(e)}, status=503)
            except Exception:
                return Response({"detail": "Не удалось загрузить лидерборд Dota 2"}, status=502)
            data = [{
                "external_id": str(p.get("account_id")),
                "name": p.get("name") or p.get("personaname"),
                "avatar": p.get("avatar"),
                "team": p.get("team_name"),
                "platform": "opendota",
                "guest_link": f"/players/guest/dota2/{p.get('account_id')}" if p.get("account_id") else None,
                "source": "OpenDota — известные про-игроки",
            } for p in players]
            cache.set("world_leaderboard_dota2", data, timeout=60 * 60)
            return Response(data)

        if game == "lol":
            from .integrations.riot_client import RiotClient
            client = RiotClient()
            league = client.get_challenger_league()
            entries = sorted(league.get("entries", []), key=lambda e: e["leaguePoints"], reverse=True)[:15]
            data = [{
                "external_id": e.get("summonerId"),
                "name": e.get("summonerName", "?"),
                "lp": e.get("leaguePoints"),
                "wins": e.get("wins"),
                "losses": e.get("losses"),
                "platform": "lol",
                "source": "Riot — Challenger EUW",
            } for e in entries]
            return Response(data)

        if game == "cs2":
            cached = cache.get("world_leaderboard_cs2")
            if cached:
                return Response(cached)

            from .integrations.faceit_client import FaceitClient
            client = FaceitClient()
            try:
                ranking = client.get_global_ranking(region="EU", limit=15)
            except Exception:
                return Response({"detail": "Не удалось загрузить лидерборд CS2"}, status=502)

            data = []
            for entry in ranking:
                player = entry.get("player", {})
                gh_account = GameAccount.objects.filter(
                    platform="faceit", external_id=player.get("nickname", "")
                ).first()
                data.append({
                    "external_id": player.get("user_id"),
                    "name": player.get("nickname", "Игрок"),
                    "avatar": player.get("avatar"),
                    "subtitle": player.get("country", "").upper(),
                    "value": f"ELO {entry.get('faceit_elo', '—')}",
                    "guest_link": None,  # у Faceit нет отдельного гостевого просмотра, только сам GameEyes-профиль, если зарегистрирован
                    "gamehub_user_id": gh_account.user_id if gh_account else None,
                })

            cache.set("world_leaderboard_cs2", data, timeout=6 * 60 * 60)
            return Response(data)
        
        if game == "valorant":
            cached = cache.get("world_leaderboard_valorant")
            if cached:
                return Response(cached)

            from .integrations.valorant_client import ValorantClient
            client = ValorantClient()
            try:
                players = client.get_leaderboard(region="eu", size=15)
            except Exception:
                return Response({"detail": "Не удалось загрузить лидерборд Valorant"}, status=502)

            data = []
            for p in players:
                riot_id = f"{p.get('gameName')}#{p.get('tagLine')}"
                gh_account = GameAccount.objects.filter(platform="valorant", external_id__iexact=riot_id).first()
                data.append({
                    "external_id": riot_id,
                    "name": p.get("gameName", "Игрок"),
                    "avatar": None,
                    "subtitle": f"#{p.get('leaderboardRank')}",
                    "value": f"{p.get('rankedRating', 0)} RR",
                    "guest_link": None,
                    "gamehub_user_id": gh_account.user_id if gh_account else None,
                })

            cache.set("world_leaderboard_valorant", data, timeout=6 * 60 * 60)
            return Response(data)

        return Response([], status=200)

class GuestProfileView(APIView):
    """
    GET /api/guest-profile/dota2/{account_id}/
    GET /api/guest-profile/valorant/{Name%23Tag}/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, game, external_id):
        game = (game or "").lower()
        if game in ("opendota", "dota"):
            game = "dota2"
        if game == "dota2":
            return self._dota_guest(external_id)
        if game == "valorant":
            return self._valorant_guest(external_id)
        return Response(
            {"detail": "Гостевой просмотр поддерживается для dota2 и valorant"},
            status=400,
        )

    def _dota_guest(self, external_id):
        from .integrations.opendota_client import OpenDotaClient
        from datetime import datetime

        client = OpenDotaClient()
        try:
            player = client.get_player(external_id)
            wl = client.get_win_loss(external_id)
        except Exception:
            return Response(
                {"detail": "Игрок не найден или профиль полностью закрыт"},
                status=404,
            )

        profile_data = player.get("profile", {}) or {}
        is_public = bool(profile_data.get("personaname"))

        heroes_data = []
        hero_names = {}
        try:
            heroes_raw = client.get_heroes(external_id)
            hero_names = client.get_hero_names()
            top = sorted(heroes_raw, key=lambda h: h.get("games", 0), reverse=True)[:5]
            heroes_data = [
                {
                    "name": hero_names.get(h["hero_id"], "?"),
                    "games": h.get("games", 0),
                    "winrate": round(h["win"] / h["games"] * 100, 1) if h.get("games") else 0,
                }
                for h in top
                if h.get("games", 0) > 0
            ]
        except Exception:
            pass

        match_history = []
        try:
            if not hero_names:
                hero_names = client.get_hero_names()
            recent = client.get_recent_matches(external_id, limit=20)
            for m in recent:
                is_radiant = m.get("player_slot", 0) < 128
                won = (is_radiant and m.get("radiant_win")) or (
                    not is_radiant and not m.get("radiant_win")
                )
                played_at = None
                if m.get("start_time"):
                    try:
                        played_at = datetime.fromtimestamp(m["start_time"]).strftime("%d.%m.%Y")
                    except (OSError, ValueError, OverflowError):
                        played_at = None
                match_history.append({
                    "won": won,
                    "title": hero_names.get(m.get("hero_id"), "?"),
                    "subtitle": f"{m.get('kills', 0)}/{m.get('deaths', 0)}/{m.get('assists', 0)}",
                    "match_id": m.get("match_id"),
                    "duration": f"{round(m.get('duration', 0) / 60)} мин" if m.get("duration") else None,
                    "played_at": played_at,
                })
        except Exception:
            pass

        gh_account = GameAccount.objects.filter(
            platform="opendota", external_id=str(external_id)
        ).select_related("user").first()

        return Response({
            "is_public": is_public,
            "display_name": profile_data.get("personaname") if is_public else None,
            "avatar_url": profile_data.get("avatarfull") if is_public else None,
            "is_gamehub_user": bool(gh_account),
            "gamehub_user_id": gh_account.user_id if gh_account else None,
            "wins": wl.get("win", 0),
            "losses": wl.get("lose", 0),
            "mmr_estimate": (player.get("mmr_estimate") or {}).get("estimate"),
            "rank_tier": player.get("rank_tier"),
            "top_heroes": heroes_data,
            "match_history": match_history,
        })

    def _valorant_guest(self, riot_id):
        from urllib.parse import unquote
        from collections import Counter
        from datetime import datetime
        from .integrations.valorant_client import ValorantClient

        riot_id = unquote(riot_id)
        if "#" not in riot_id:
            return Response(
                {"detail": "Укажи Riot ID в формате Ник#Тег"},
                status=400,
            )
        name, tag = riot_id.split("#", 1)
        client = ValorantClient()

        try:
            account = client.get_account(name, tag)
        except Exception as e:
            return Response(
                {"detail": str(e) or "Игрок не найден"},
                status=404,
            )

        region = account.get("region") or "eu"
        mmr, matches = {}, []
        try:
            mmr = client.get_mmr(name, tag, region=region) or {}
        except Exception:
            pass
        try:
            matches = client.get_matches(name, tag, region=region, size=20) or []
        except Exception:
            pass

        current = mmr.get("current_data") or {}
        tier = current.get("currenttierpatched") or "Unranked"
        rr = current.get("ranking_in_tier") or 0

        agent_counter = Counter()
        match_history = []
        wins = losses = 0

        for match in matches[:20]:
            players = (match.get("players") or {}).get("all_players") or []
            me = next(
                (p for p in players if (p.get("name") or "").lower() == name.lower()),
                None,
            )
            if not me:
                continue

            team_key = (me.get("team") or "").lower()
            team_won = bool(
                (match.get("teams") or {}).get(team_key, {}).get("has_won", False)
            )
            if team_won:
                wins += 1
            else:
                losses += 1

            agent = me.get("character") or "?"
            agent_counter[agent] += 1
            stats = me.get("stats") or {}
            k = stats.get("kills", 0)
            d = stats.get("deaths", 0)
            a = stats.get("assists", 0)

            meta = match.get("metadata") or {}
            game_start = meta.get("game_start")
            played_at = None
            if game_start:
                try:
                    played_at = datetime.fromtimestamp(game_start).strftime("%d.%m.%Y")
                except (OSError, ValueError, OverflowError):
                    played_at = None

            match_id = meta.get("matchid") or meta.get("match_id")
            match_history.append({
                "won": team_won,
                "title": agent,
                "subtitle": f"{k}/{d}/{a}",
                "match_id": match_id,
                "played_at": played_at,
                "duration": None,
            })

        top_heroes = [
            {"name": ag, "games": cnt, "winrate": 0}
            for ag, cnt in agent_counter.most_common(5)
        ]

        gh_account = GameAccount.objects.filter(
            platform="valorant", external_id__iexact=f"{name}#{tag}"
        ).select_related("user").first()

        avatar = None
        card = account.get("card")
        if isinstance(card, dict):
            avatar = card.get("small") or card.get("large")
        if not avatar:
            avatar = account.get("avatar")

        return Response({
            "is_public": True,
            "display_name": f"{name}#{tag}",
            "avatar_url": avatar,
            "is_gamehub_user": bool(gh_account),
            "gamehub_user_id": gh_account.user_id if gh_account else None,
            "wins": wins,
            "losses": losses,
            "mmr_estimate": None,
            "tier": tier,
            "rr": rr,
            "rank_tier": None,
            "top_heroes": top_heroes,
            "match_history": match_history,
        })


class MatchParticipantsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, game, match_id):
        if game == "dota2":
            return self._dota_participants(match_id)
        if game == "valorant":
            return self._valorant_participants(match_id)
        return Response({"detail": "Игра не поддерживается"}, status=400)

    def _dota_participants(self, match_id):
        from .integrations.opendota_client import OpenDotaClient, OpenDotaError
        from .integrations.steam_client import SteamClient

        client = OpenDotaClient()
        try:
            detail = client.get_match_details(match_id)
        except OpenDotaError as e:
            return Response({"detail": str(e)}, status=503)
        except Exception:
            return Response({"detail": "Матч не найден"}, status=404)

        try:
            hero_names = client.get_hero_names()
        except Exception:
            hero_names = {}

        try:
            item_names = client.get_item_names()
        except Exception:
            item_names = {}

        players_raw = detail.get("players", []) or []
        steam_ids = [
            str(p["account_id"] + 76561197960265728)
            for p in players_raw
            if p.get("account_id")
        ]
        avatars_by_steamid = {}
        if steam_ids:
            try:
                steam_client = SteamClient()
                summaries = steam_client.get_player_summaries(steam_ids)
                for s in summaries:
                    avatars_by_steamid[s["steamid"]] = s.get("avatarfull")
            except Exception:
                pass

        participants = []
        for p in players_raw:
            account_id = p.get("account_id")
            gh_account = None
            if account_id:
                gh_account = GameAccount.objects.filter(
                    platform="opendota", external_id=str(account_id)
                ).select_related("user").first()

            is_public = bool(p.get("personaname"))
            if gh_account:
                display_name = gh_account.user.username
            elif is_public:
                display_name = p.get("personaname")
            else:
                display_name = None

            avatar = None
            if account_id:
                avatar = avatars_by_steamid.get(str(account_id + 76561197960265728))

            items = []
            for slot in range(6):
                item_id = p.get(f"item_{slot}")
                if item_id and item_id in item_names:
                    items.append(item_names[item_id])

            neutral = None
            nid = p.get("item_neutral")
            if nid and nid in item_names:
                neutral = item_names[nid]

            participants.append({
                "account_id": account_id,
                "display_name": display_name,
                "avatar": avatar,
                "hero": hero_names.get(p.get("hero_id"), f"Hero {p.get('hero_id')}"),
                "level": p.get("level"),
                "kda": f"{p.get('kills', 0)}/{p.get('deaths', 0)}/{p.get('assists', 0)}",
                "net_worth": p.get("net_worth"),
                "hero_damage": p.get("hero_damage"),
                "tower_damage": p.get("tower_damage"),
                "hero_healing": p.get("hero_healing"),
                "last_hits": p.get("last_hits"),
                "denies": p.get("denies"),
                "gpm": p.get("gold_per_min"),
                "xpm": p.get("xp_per_min"),
                "items": items or [],
                "neutral_item": neutral,
                "aghanims_scepter": bool(p.get("aghanims_scepter")),
                "aghanims_shard": bool(p.get("aghanims_shard")),
                "moonshard": bool(p.get("moonshard")),
                "is_radiant": p.get("player_slot", 0) < 128,
                "is_gamehub_user": bool(gh_account),
                "gamehub_user_id": gh_account.user_id if gh_account else None,
                "is_anonymous": account_id is None,
            })

        return Response({
            "participants": participants,
            "radiant_win": detail.get("radiant_win"),
            "duration": detail.get("duration"),
        })

    def _valorant_participants(self, match_id):
        from .integrations.valorant_client import ValorantClient
        client = ValorantClient()
        try:
            detail = client.get_match_details(match_id)
        except Exception:
            return Response({"detail": "Матч не найден"}, status=404)

        players = detail.get("players", {}).get("all_players", []) or []
        puuid_to_name = {p.get("puuid"): f"{p.get('name')}#{p.get('tag')}" for p in players}
        puuid_to_agent = {p.get("puuid"): p.get("character") for p in players}
        puuid_to_avatar = {
            p.get("puuid"): (p.get("assets") or {}).get("card", {}).get("small")
            for p in players
        }
        puuid_to_team = {p.get("puuid"): p.get("team") for p in players}

        participants = []
        for p in players:
            riot_id = f"{p.get('name')}#{p.get('tag')}"
            gh_account = GameAccount.objects.filter(
                platform="valorant", external_id__iexact=riot_id
            ).select_related("user").first()
            stats = p.get("stats") or {}
            participants.append({
                "riot_id": riot_id,
                "display_name": p.get("name"),
                "avatar": (p.get("assets") or {}).get("card", {}).get("small"),
                "agent": p.get("character"),
                "team": p.get("team"),
                "kda": f"{stats.get('kills', 0)}/{stats.get('deaths', 0)}/{stats.get('assists', 0)}",
                "is_gamehub_user": bool(gh_account),
                "gamehub_user_id": gh_account.user_id if gh_account else None,
            })

        rounds_data = []
        for i, rnd in enumerate(detail.get("rounds", []) or []):
            # --- плант ---
            plant = rnd.get("plant_events") or {}
            if isinstance(plant, list):
                plant = plant[0] if plant else {}
            plant_time = plant.get("plant_time_in_round")
            plant_site = plant.get("plant_site")
            planter_info = plant.get("planted_by") or {}
            planter_puuid = planter_info.get("puuid") if isinstance(planter_info, dict) else None

            # кто атакует в этом раунде
            attacking_team = None
            if planter_puuid and planter_puuid in puuid_to_team:
                attacking_team = puuid_to_team[planter_puuid]
            if not attacking_team:
                # до смены сторон (раунды 0–11) обычно Red атакует
                attacking_team = "Red" if i < 12 else "Blue"
            defending_team = "Blue" if attacking_team == "Red" else "Red"

            kills = []
            for player_stat in rnd.get("player_stats", []) or []:
                for kill_event in player_stat.get("kill_events", []) or []:
                    killer_puuid = kill_event.get("killer_puuid")
                    victim_puuid = kill_event.get("victim_puuid")
                    killer_team = puuid_to_team.get(killer_puuid)
                    side = "attack" if killer_team == attacking_team else "defense"

                    kills.append({
                        "killer": puuid_to_name.get(killer_puuid, "?"),
                        "victim": puuid_to_name.get(victim_puuid, "?"),
                        "killer_agent": puuid_to_agent.get(killer_puuid, "?"),
                        "victim_agent": puuid_to_agent.get(victim_puuid, "?"),
                        "killer_avatar": puuid_to_avatar.get(killer_puuid),
                        "victim_avatar": puuid_to_avatar.get(victim_puuid),
                        "weapon": kill_event.get("damage_weapon_name"),
                        "headshot": kill_event.get("kill_type") == "headshot",
                        "time_in_round": kill_event.get("kill_time_in_round"),
                        "side": side,
                        "killer_team": killer_team,
                    })

            kills.sort(key=lambda k: k.get("time_in_round") or 0)

            # таймлайн: киллы + плант
            events = [{**k, "type": "kill"} for k in kills]
            if plant_time is not None:
                events.append({
                    "type": "plant",
                    "time_in_round": plant_time,
                    "site": plant_site or "?",
                    "planter": puuid_to_name.get(planter_puuid, "?") if planter_puuid else "?",
                    "side": "attack",
                })
            events.sort(key=lambda e: e.get("time_in_round") or 0)

            winning = rnd.get("winning_team") or rnd.get("end_result")
            rounds_data.append({
                "round_number": i + 1,
                "winning_team": winning,
                "attacking_team": attacking_team,
                "defending_team": defending_team,
                "plant_time": plant_time,
                "plant_site": plant_site,
                "kills": kills,
                "events": events,
            })

        teams = detail.get("teams") or {}
        red_team = teams.get("red") or {}
        blue_team = teams.get("blue") or {}

        return Response({
            "participants": participants,
            "map": (detail.get("metadata") or {}).get("map"),
            "red_won": red_team.get("has_won"),
            "blue_won": blue_team.get("has_won"),
            "red_score": red_team.get("rounds_won", 0),
            "blue_score": blue_team.get("rounds_won", 0),
            "rounds": rounds_data,
        })
class RecentMatchesFeedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        platform = request.query_params.get("platform")
        accounts = GameAccount.objects.filter(user=request.user)
        if platform:
            accounts = accounts.filter(platform=platform)

        all_matches = []
        for acc in accounts:
            history = (acc.extra_stats or {}).get("match_history", [])
            for m in history[:8]:
                all_matches.append({**m, "game_label": acc.game_label or acc.platform, "platform": acc.platform})

        all_matches.sort(key=lambda m: m.get("played_at") or "", reverse=True)

        available_platforms = list(
            GameAccount.objects.filter(user=request.user)
            .exclude(extra_stats__isnull=True)
            .values_list("platform", "game_label")
            .distinct()
        )

        return Response({
            "matches": all_matches[:8],
            "available_platforms": [{"value": p, "label": l or p} for p, l in available_platforms],
        })
  