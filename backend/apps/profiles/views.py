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
        if request.user.id != user.id:
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
            from .integrations.opendota_client import OpenDotaClient
            client = OpenDotaClient()
            players = client.get_pro_players()[:15]
            data = [{
                "external_id": str(p.get("account_id")),
                "name": p.get("name") or p.get("personaname"),
                "avatar": p.get("avatar"),
                "team": p.get("team_name"),
                "platform": "opendota",
                "source": "OpenDota — известные про-игроки",
            } for p in players]
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

        return Response([], status=200)

class GuestProfileView(APIView):
    """GET /api/guest-profile/dota2/{external_id}/ — статистика ЛЮБОГО игрока, зарегистрирован он или нет"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, game, external_id):
        if game != "dota2":
            return Response({"detail": "Гостевой просмотр поддерживается только для Dota 2"}, status=400)

        from .integrations.opendota_client import OpenDotaClient
        from .integrations.steam_client import SteamClient

        client = OpenDotaClient()
        try:
            player = client.get_player(external_id)
            wl = client.get_win_loss(external_id)
        except Exception:
            return Response({"detail": "Игрок не найден или профиль полностью закрыт"}, status=404)

        profile_data = player.get("profile", {}) or {}
        is_public = bool(profile_data.get("personaname"))

        heroes_data = []
        try:
            heroes_raw = client.get_heroes(external_id)
            hero_names = client.get_hero_names()
            top = sorted(heroes_raw, key=lambda h: h.get("games", 0), reverse=True)[:5]
            heroes_data = [
                {"name": hero_names.get(h["hero_id"], "?"), "games": h.get("games", 0),
                 "winrate": round(h["win"] / h["games"] * 100, 1) if h.get("games") else 0}
                for h in top if h.get("games", 0) > 0
            ]
        except Exception:
            pass

        gh_account = GameAccount.objects.filter(platform="opendota", external_id=str(external_id)).select_related("user").first()

        return Response({
            "is_public": is_public,
            "display_name": profile_data.get("personaname") if is_public else None,
            "avatar_url": profile_data.get("avatarfull") if is_public else None,
            "is_gamehub_user": bool(gh_account),
            "gamehub_user_id": gh_account.user_id if gh_account else None,
            "wins": wl.get("win", 0),
            "losses": wl.get("lose", 0),
            "mmr_estimate": player.get("mmr_estimate", {}).get("estimate"),
            "rank_tier": player.get("rank_tier"),
            "top_heroes": heroes_data,
        })

class WorldLeaderboardView(APIView):
    """GET /api/world-leaderboard/?game=dota2|lol"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        game = request.query_params.get("game", "dota2")

        if game == "dota2":
            cached = cache.get("world_leaderboard_dota2")
            if cached:
                return Response(cached)

            from .integrations.opendota_client import OpenDotaClient
            client = OpenDotaClient()
            try:
                players = client.get_pro_players()
            except Exception:
                return Response({"detail": "Не удалось загрузить лидерборд Dota 2"}, status=502)

            enriched = []
            for p in players[:15]:  # только 15, без лишней нагрузки на API
                account_id = p.get("account_id")
                if not account_id:
                    continue
                mmr = None
                try:
                    full_profile = client.get_player(account_id)
                    mmr = full_profile.get("mmr_estimate", {}).get("estimate")
                except Exception:
                    pass  # у части профилей MMR скрыт — это нормально, просто не показываем цифру

                enriched.append({
                    "external_id": str(account_id),
                    "name": p.get("name") or p.get("personaname") or "Игрок",
                    "avatar": p.get("avatar"),
                    "subtitle": p.get("team_name") or "Свободный агент",
                    "value": f"{mmr} MMR" if mmr else None,
                    "guest_link": f"/players/guest/dota2/{account_id}",
                })

            # сортируем тех, у кого MMR известен, наверх; у кого нет — оставляем внизу как есть
            enriched.sort(key=lambda e: int(e["value"].split()[0]) if e["value"] else -1, reverse=True)

            cache.set("world_leaderboard_dota2", enriched, timeout=6 * 60 * 60)  # кэш на 6 часов
            return Response(enriched)

class MatchParticipantsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, game, match_id):
        if game == "dota2":
            return self._dota_participants(match_id)
        if game == "valorant":
            return self._valorant_participants(match_id)
        if game =="lol":
            return self._lol_participants(match_id)
        return Response({"detail": "Игра не поддерживается"}, status=400)

    def _lol_participants(self, match_id):
        from .integrations.riot_client import RiotClient
        client = RiotClient()
        try:
            match = client.get_match_details(match_id)
            timeline = client.get_match_timeline(match_id)
        except Exception:
            return Response({"detail": "Матч не найден"}, status=404)

        participant_id_to_name = {
            p["participantId"]: p["riotIdGameName"] for p in match["info"]["participants"]
        }

        kill_events = []
        for frame in timeline.get("info", {}).get("frames", []):
            for event in frame.get("events", []):
                if event.get("type") == "CHAMPION_KILL":
                    kill_events.append({
                        "killer": participant_id_to_name.get(event.get("killerId"), "Environment"),
                        "victim": participant_id_to_name.get(event.get("victimId"), "?"),
                        "timestamp_ms": event.get("timestamp"),
                    })

        participants = []
        for p in match["info"]["participants"]:
            gh_account = GameAccount.objects.filter(
                platform="lol", external_id__istartswith=p.get("riotIdGameName", "")
            ).select_related("user").first()
            participants.append({
                "name": p.get("riotIdGameName"),
                "champion": p.get("championName"),
                "kda": f"{p.get('kills',0)}/{p.get('deaths',0)}/{p.get('assists',0)}",
                "team": p.get("teamId"),
                "won": p.get("win"),
                "is_gamehub_user": bool(gh_account),
                "gamehub_user_id": gh_account.user_id if gh_account else None,
            })

        return Response({"participants": participants, "kill_timeline": kill_events})

    def _valorant_participants(self, match_id):
        from .integrations.valorant_client import ValorantClient
        client = ValorantClient()
        try:
            detail = client.get_match_details(match_id)
        except Exception:
            return Response({"detail": "Матч не найден"}, status=404)

        players = detail.get("players", {}).get("all_players", [])
        puuid_to_name = {p.get("puuid"): f"{p.get('name')}#{p.get('tag')}" for p in players}

        participants = []
        for p in players:
            riot_id = f"{p.get('name')}#{p.get('tag')}"
            gh_account = GameAccount.objects.filter(platform="valorant", external_id__iexact=riot_id).select_related("user").first()
            stats = p.get("stats", {})
            participants.append({
                "riot_id": riot_id,
                "display_name": p.get("name"),
                "avatar": p.get("assets", {}).get("card", {}).get("small"),
                "agent": p.get("character"),
                "team": p.get("team"),
                "kda": f"{stats.get('kills',0)}/{stats.get('deaths',0)}/{stats.get('assists',0)}",
                "is_gamehub_user": bool(gh_account),
                "gamehub_user_id": gh_account.user_id if gh_account else None,
            })

        # раунды с покилловой разбивкой — структура HenrikDev может отличаться версией API,
        # если поля не совпадут, пришли сырой detail.get("rounds") и я поправлю маппинг
        rounds_data = []
        for i, rnd in enumerate(detail.get("rounds", [])):
            kills = []
            for player_stat in rnd.get("player_stats", []):
                for kill_event in player_stat.get("kill_events", []) or []:
                    killer = puuid_to_name.get(kill_event.get("killer_puuid"), "?")
                    victim = puuid_to_name.get(kill_event.get("victim_puuid"), "?")
                    kills.append({
                        "killer": killer, "victim": victim,
                        "weapon": kill_event.get("damage_weapon_name"),
                        "time_in_round": kill_event.get("kill_time_in_round"),
                    })
            rounds_data.append({"round_number": i + 1, "winning_team": rnd.get("end_result"), "kills": kills})

        teams = detail.get("teams", {})
        return Response({
            "participants": participants,
            "map": detail.get("metadata", {}).get("map"),
            "red_won": teams.get("red", {}).get("has_won"),
            "blue_won": teams.get("blue", {}).get("has_won"),
            "rounds": rounds_data,
        })

    def _dota_participants(self, match_id):
        from .integrations.opendota_client import OpenDotaClient
        from .integrations.steam_client import SteamClient

        client = OpenDotaClient()
        try:
            detail = client.get_match_details(match_id)
        except Exception:
            return Response({"detail": "Матч не найден"}, status=404)

        hero_names = client.get_hero_names()
        try:
            item_names = client.get_item_names()
        except Exception:
            item_names = {}

        players_raw = detail.get("players", [])

        
        steam_ids = [str(p["account_id"] + 76561197960265728) for p in players_raw if p.get("account_id")]
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
                if item_id:
                    items.append(item_names.get(item_id, f"Предмет #{item_id}"))

            participants.append({
                "account_id": account_id,
                "display_name": display_name,
                "avatar": avatar,
                "hero": hero_names.get(p.get("hero_id"), "?"),
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
                "items": items,
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