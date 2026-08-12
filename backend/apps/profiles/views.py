from django.shortcuts import render
from django.core.cache import cache
from rest_framework import viewsets,permissions,status 
from rest_framework.decorators import action 
from rest_framework.response import Response 
from rest_framework.views import APIView

from .models import GameAccount
from .serializers import GameAccountSerializer
from .serivces import ProfileSyncService,SyncError,get_account_summary
from .tasks import sync_single_account

SYNC_COOLDOWN_SECONDS =300
LIST_CACHE_TIMEOUT = 120
MAX_ACCOUNTS_PER_PLATFORM = 1

def _list_cache_key(user_id):
    return f'game_accounts:{user_id}'

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
                {"detail": "Синхронизация уже запускалась недавно, попробуй через несколько минут"},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        try:
            ProfileSyncService(account).sync()
        except SyncError as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        cache.set(cooldown_key, True, timeout=SYNC_COOLDOWN_SECONDS)
        cache.delete(_list_cache_key(request.user.id))

        return Response(self.get_serializer(account).data)
    
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
        from apps.users.models import ProfileView
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Игрок не найден"}, status=404)

        # засчитываем просмотр, только если смотрит НЕ сам владелец профиля
        views_count = ProfileView.objects.filter(viewed_user=user).count()
        if request.user.id != user.id:
            ProfileView.objects.create(viewer=request.user, viewed_user=user)
            views_count += 1

        accounts = GameAccount.objects.filter(user=user).prefetch_related("snapshots")
        profile = getattr(user, "profile", None)

        return Response({
            "username": user.username,
            "display_name": profile.display_name if profile else user.username,
            "avatar_url": profile.avatar_url if profile else None,
            "views_count": views_count,
            "accounts": GameAccountSerializer(accounts, many=True, context={"request": request}).data,
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

        return Response([], status=200)

class GuestProfileView(APIView):
    """GET /api/guest-profile/dota2/{account_id}/ — статистика игрока, даже если он не на GameHub"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, game, external_id):
        if game == "dota2":
            from .integrations.opendota_client import OpenDotaClient
            client = OpenDotaClient()
            try:
                player = client.get_player(external_id)
                wl = client.get_win_loss(external_id)
            except Exception:
                return Response({"detail": "Игрок не найден"}, status=404)

            return Response({
                "display_name": player.get("profile", {}).get("personaname", "Неизвестно"),
                "avatar_url": player.get("profile", {}).get("avatarfull"),
                "is_registered_on_gamehub": GameAccount.objects.filter(platform="opendota", external_id=external_id).exists(),
                "stats": {
                    "wins": wl.get("win", 0),
                    "losses": wl.get("lose", 0),
                    "mmr_estimate": player.get("mmr_estimate", {}).get("estimate"),
                    "rank_tier": player.get("rank_tier"),
                },
            })

        return Response({"detail": "Платформа не поддерживает гостевой просмотр"}, status=400)

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
        if game != "dota2":
            return Response({"detail": "Игра не поддерживается"}, status=400)

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