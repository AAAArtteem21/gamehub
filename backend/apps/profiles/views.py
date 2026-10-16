from django.shortcuts import render
from django.core.cache import cache
from rest_framework import viewsets,permissions,status 
from rest_framework.decorators import action 
from rest_framework.response import Response 
from rest_framework.views import APIView
import threading
from django.core.cache import cache
from .related import (
    related_games_for_steam32,
    related_games_for_riot,
    steam64_to_32,
    steam32_to_64,
)
from apps.users.display import user_public_name
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
    user_id = None
    try:
        account = GameAccount.objects.get(id=account_id)
        user_id = account.user_id
        ProfileSyncService(account).sync()
        cache.set(f"sync_status:{account_id}", {"status": "done"}, timeout=300)
    except Exception as e:
        cache.set(
            f"sync_status:{account_id}",
            {"status": "error", "detail": str(e)},
            timeout=300,
        )
    finally:
        cache.delete(f"profile_sync_cooldown:{account_id}")
        if user_id is not None:
            cache.delete(_list_cache_key(user_id))


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
        
    def create(self, request, *args, **kwargs):
        platform = request.data.get("platform")
        external_id = (request.data.get("external_id") or "").strip()

        # Steam: никогда не создаём второй аккаунт — синкаем существующий
        if platform == "steam":
            existing = GameAccount.objects.filter(
                user=request.user, platform="steam"
            ).first()
            if existing:
                if external_id and str(existing.external_id) != external_id:
                    existing.external_id = external_id
                    existing.save(update_fields=["external_id"])
                service = None
                try:
                    service = ProfileSyncService(existing)
                    service.sync()
                except SyncError as e:
                    cache.delete(_list_cache_key(request.user.id))
                    data = self.get_serializer(existing).data
                    return Response(
                        {**data, "account": data, "sync_error": str(e), "linked": []},
                        status=status.HTTP_200_OK,
                    )
                except Exception:
                    pass

                cache.delete(_list_cache_key(request.user.id))
                existing.refresh_from_db()
                data = self.get_serializer(existing).data
                linked = [
                    {
                        "platform": a.platform,
                        "id": a.id,
                        "status": "syncing",
                        "nickname": a.nickname,
                    }
                    for a in (service.linked_accounts if service else [])
                ]
                return Response(
                    {**data, "account": data, "linked": linked},
                    status=status.HTTP_200_OK,
                )

        existing_count = GameAccount.objects.filter(
            user=request.user, platform=platform
        ).count()
        if existing_count >= MAX_ACCOUNTS_PER_PLATFORM:
            return Response(
                {"detail": f"Уже подключен аккаунт для платформы {platform}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = super().create(request, *args, **kwargs)
        service = None

        if platform == "steam":
            try:
                account = GameAccount.objects.get(id=response.data["id"])
                service = ProfileSyncService(account)
                service.sync()
                response.data["account"] = self.get_serializer(account).data
            except SyncError as e:
                response.data["sync_error"] = str(e)
            except Exception:
                pass
            response.data["linked"] = [
                {
                    "platform": a.platform,
                    "id": a.id,
                    "status": "syncing",
                    "nickname": a.nickname,
                }
                for a in (service.linked_accounts if service else [])
            ]

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
    permission_classes = [permissions.AllowAny]

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
                "username": user_public_name(acc.user),
                "platform": acc.platform,
                "skill_rating": acc.skill_rating,
                "matches": matches,
                "winrate": winrate,
            })
        return Response(data)
class PublicProfileView(APIView):
    """GET /api/players/<user_id>/ — публичный профиль (как свой, без приватных действий)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        from django.contrib.auth import get_user_model
        from .models import GameAccount
        from .serivces import build_display_stats  # если файл services.py — from .services import ...

        User = get_user_model()
        try:
            target = User.objects.select_related("profile").get(pk=user_id)
        except User.DoesNotExist:
            return Response({"detail": "Пользователь не найден"}, status=404)

        profile = getattr(target, "profile", None)

        # --- прогресс GH (без реф-кода) ---
        progress = None
        if profile is not None:
            level = getattr(profile, "level", 1) or 1
            xp_total = getattr(profile, "xp", 0) or 0
            xp_per = getattr(profile, "xp_per_level", None) or 100
            if xp_per <= 0:
                xp_per = 100
            # если хранится xp_into_level — используй его, иначе посчитай
            xp_into = getattr(profile, "xp_into_level", None)
            if xp_into is None:
                xp_into = xp_total % xp_per
            pct = min(100, round(xp_into / xp_per * 100, 1)) if xp_per else 0
            tags = getattr(profile, "tags", None) or []
            if callable(tags):
                tags = tags()
            progress = {
                "level": level,
                "xp_into_level": xp_into,
                "xp_per_level": xp_per,
                "pct": pct,
                "tags": list(tags) if tags else [],
            }

        # --- просмотры (опционально) ---
        views_count = 0
        try:
            from apps.users.models import ProfileView
            if request.user.id != target.id:
                ProfileView.objects.create(viewer=request.user, viewed_user=target)
            views_count = ProfileView.objects.filter(viewed_user=target).count()
        except Exception:
            pass

        # --- аккаунты + display_stats ---
        accounts_qs = (
            GameAccount.objects.filter(user=target).order_by("-created_at")
        )
        accounts_data = []
        for acc in accounts_qs:
            extra = dict(acc.extra_stats or {})
            if acc.platform == "faceit":
                extra = self._enrich_faceit_extra(extra)
            elif acc.platform == "valorant":
                extra = self._enrich_valorant_extra(extra)

            accounts_data.append({
                "id": acc.id,
                "platform": acc.platform,
                "external_id": acc.external_id,
                "nickname": acc.nickname,
                "avatar": acc.avatar,
                "verified": acc.verified,
                "game_label": acc.game_label,
                "skill_rating": acc.skill_rating,
                "last_synced_at": acc.last_synced_at,
                "display_stats": build_display_stats(acc.platform, extra),
            })

        display_name = None
        avatar_url = None
        if profile is not None:
            display_name = profile.display_name or None
            avatar_url = profile.avatar_url or None

        return Response({
            "id": target.id,
            "username": user_public_name(target),
            "display_name": display_name or user_public_name(target),
            "avatar_url": avatar_url,
            "steam_id": getattr(profile, "steam_id", None) if profile else None,
            "bio": getattr(profile, "bio", "") if profile else "",
            "progress": progress,
            "views_count": views_count,
            "is_me": request.user.id == target.id,
            "accounts": accounts_data,
        })

    @staticmethod
    def _to_int(v, default=0):
        try:
            return int(float(str(v).replace(",", ".")))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_float(v, default=None):
        if v is None or v == "":
            return default
        try:
            return float(str(v).replace(",", "."))
        except (TypeError, ValueError):
            return default

    def _enrich_faceit_extra(self, extra: dict) -> dict:
        """Avg/ADR на лету, если в extra ещё нет (старый синк)."""
        extra = dict(extra or {})
        history = extra.get("match_history") or []

        if extra.get("avg_kills") is None and history:
            n = sk = sd = sa = 0
            for m in history[:20]:
                parts = (m.get("subtitle") or "").split("·")[0].strip().split("/")
                if len(parts) >= 3:
                    sk += self._to_int(parts[0])
                    sd += self._to_int(parts[1])
                    sa += self._to_int(parts[2])
                    n += 1
            if n:
                extra["avg_kills"] = round(sk / n, 1)
                extra["avg_deaths"] = round(sd / n, 1)
                extra["avg_assists"] = round(sa / n, 1)
                extra["avg_kd_recent"] = round((sk + sa) / max(sd, 1), 2)
                extra["sample_size"] = n

        life = extra.get("lifetime") or {}
        if extra.get("adr") is None and life:
            for key in ("ADR", "Average Damage per Round", "Damage/Round"):
                if key in life and life[key] not in (None, ""):
                    val = self._to_float(life[key])
                    if val is not None:
                        extra["adr"] = round(val, 1)
                    break
        if extra.get("entry_success") is None and life:
            for key in ("Entry Success Rate", "Entry Rate %"):
                if key in life and life[key] not in (None, ""):
                    val = self._to_float(life[key])
                    if val is not None:
                        extra["entry_success"] = round(val, 1)
                    break
        if extra.get("kr") is None and life:
            for key in ("K/R Ratio", "Average K/R Ratio", "Kills/Round"):
                if key in life and life[key] not in (None, ""):
                    val = self._to_float(life[key])
                    if val is not None:
                        extra["kr"] = round(val, 2)
                    break

        return extra

    def _enrich_valorant_extra(self, extra: dict) -> dict:
        extra = dict(extra or {})
        history = extra.get("match_history") or []
        if extra.get("avg_kills") is not None or not history:
            return extra

        n = sk = sd = sa = acs_sum = 0
        for m in history[:20]:
            parts = (m.get("subtitle") or "").split("/")
            if len(parts) >= 3:
                try:
                    sk += int(parts[0])
                    sd += int(parts[1])
                    sa += int(str(parts[2]).split()[0])
                    n += 1
                except (TypeError, ValueError):
                    pass
            for det in m.get("details") or []:
                if det.get("label") == "Combat Score (ACS)":
                    try:
                        acs_sum += int(det.get("value") or 0)
                    except (TypeError, ValueError):
                        pass
        if n:
            extra["avg_kills"] = round(sk / n, 1)
            extra["avg_deaths"] = round(sd / n, 1)
            extra["avg_assists"] = round(sa / n, 1)
            extra["avg_kd_recent"] = round((sk + sa) / max(sd, 1), 2)
            extra["avg_acs"] = round(acs_sum / n) if acs_sum else None
            extra["sample_size"] = n
        return extra
class WorldLeaderboardView(APIView):
    """
    GET /api/world-leaderboard/?game=dota2|lol — топ игроков из открытых источников,
    включая тех, кто никогда не регистрировался на GameHub
    """
    permission_classes = [permissions.AllowAny]

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
                    "external_id": player.get("nickname") or player.get("user_id"),
                    "name": player.get("nickname", "Игрок"),
                    "avatar": player.get("avatar"),
                    "subtitle": player.get("country", "").upper(),
                    "value": f"ELO {entry.get('faceit_elo', '—')}",
                    "guest_link": (
                        f"/players/guest/faceit/{player.get('nickname')}"
                        if player.get("nickname")
                        else None
                    ),
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
                from urllib.parse import quote
                data.append({
                    "external_id": riot_id,
                    "name": p.get("gameName", "Игрок"),
                    "avatar": None,
                    "subtitle": f"#{p.get('leaderboardRank')}",
                    "value": f"{p.get('rankedRating', 0)} RR",
                    "guest_link": f"/players/guest/valorant/{quote(riot_id, safe='')}",
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
    permission_classes = [permissions.AllowAny]

    def get(self, request, game, external_id):
        g = str(game or "").lower().strip()
        if g in ("dota2", "opendota", "dota"):
            return self._dota_guest(external_id)
        if g == "valorant":
            return self._valorant_guest(external_id)
        if g == "faceit":
            return self._faceit_guest(external_id)
        if g == "deadlock":
            return self._deadlock_guest(external_id)
        return Response(
            {"detail": "Гостевой просмотр поддерживается для Dota 2, Valorant, Faceit, Deadlock"},
            status=400,
        )

    def _deadlock_guest(self, external_id):
        """
        Гостевой Deadlock: rank + history + Steam ник/аватар + related_games.
        Пустые данные → 200, не 404.
        """
        from datetime import datetime
        from collections import Counter
        from django.core.cache import cache
        from .integrations.deadlock_client import (
            DeadlockClient,
            DeadlockError,
            DeadlockRateLimited,
        )
        from .serivces import build_display_stats

        raw = str(external_id or "").strip()
        if raw.startswith("7656119"):
            try:
                account_id = str(int(raw) & 0xFFFFFFFF)
            except (TypeError, ValueError):
                account_id = raw
        else:
            account_id = raw

        if not str(account_id).isdigit():
            return Response(
                {"detail": "Некорректный Deadlock / Steam32 id"},
                status=400,
            )

        cache_key = f"deadlock:guest:{account_id}:v4"
        cached = cache.get(cache_key)

        if cached is None:
            client = DeadlockClient()
            try:
                rank_raw = client.get_rank(account_id) or {}
            except (DeadlockRateLimited, DeadlockError, Exception):
                rank_raw = {}

            try:
                matches_raw = client.get_match_history(account_id) or []
            except (DeadlockRateLimited, DeadlockError, Exception):
                matches_raw = []

            if isinstance(matches_raw, dict):
                matches_raw = (
                    matches_raw.get("matches")
                    or matches_raw.get("data")
                    or matches_raw.get("history")
                    or []
                )
            if not isinstance(matches_raw, list):
                matches_raw = []

            cached = {
                "rank": rank_raw if isinstance(rank_raw, dict) else {},
                "matches": matches_raw,
            }
            cache.set(cache_key, cached, 600)

        rank_raw = cached.get("rank") or {}
        matches_raw = cached.get("matches") or []

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

        hero_names = cache.get("deadlock:hero_names") or {}
        if hero_names and any(not isinstance(k, str) for k in hero_names.keys()):
            hero_names = {str(k): v for k, v in hero_names.items()}
            cache.set("deadlock:hero_names", hero_names, 3600)

        if not hero_names:
            try:
                client = DeadlockClient()
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

            match_history.append({
                "won": won,
                "title": hname,
                "subtitle": f"{k}/{d}/{a}",
                "duration": duration,
                "match_id": str(mid) if mid is not None else None,
                "played_at": played_at,
            })

        total = wins + losses
        winrate = round(wins / total * 100, 1) if total else 0
        top_heroes = [{"name": n, "games": c} for n, c in hero_counter.most_common(8)]

        display_name = f"Player {account_id}"
        avatar_url = None
        try:
            from .integrations.steam_client import SteamClient
            sid64 = str(int(account_id) + 76561197960265728)
            rows = SteamClient().get_player_summaries([sid64]) or []
            if rows:
                if rows[0].get("personaname"):
                    display_name = rows[0]["personaname"]
                av = (
                    rows[0].get("avatarfull")
                    or rows[0].get("avatarmedium")
                    or rows[0].get("avatar")
                )
                if av:
                    avatar_url = av
        except Exception:
            pass

        detail_hint = None
        if not match_history and badge == 0:
            detail_hint = (
                "По этому Steam ID пока нет матчей Deadlock в API "
                "(или мало данных). Это не «профиль скрыт»."
            )

        extra = {
            "matches": total if total else len(match_history),
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "tier": tier,
            "badge": badge,
            "subrank": subrank,
            "top_heroes": top_heroes,
            "match_history": match_history,
        }

        gh = (
            GameAccount.objects.filter(platform="deadlock", external_id=str(account_id))
            .select_related("user", "user__profile")
            .first()
        )

        return Response({
            "is_public": True,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "is_gamehub_user": bool(gh),
            "gamehub_user_id": gh.user_id if gh else None,
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "tier": tier,
            "badge": badge,
            "mmr_estimate": None,
            "rank_tier": None,
            "top_heroes": top_heroes,
            "match_history": match_history,
            "display_stats": build_display_stats("deadlock", extra),
            "related_games": related_games_for_steam32(account_id, current="deadlock"),
            "detail_hint": detail_hint,
            "is_empty": not match_history and wins == 0 and losses == 0 and badge == 0,
        }, status=200)

    def _faceit_guest(self, external_id):
        from datetime import datetime
        from .integrations.faceit_client import FaceitClient, FaceitError
        from .serivces import build_display_stats

        raw = str(external_id or "").strip()
        if not raw:
            return Response({"detail": "Нет id"}, status=400)

        client = FaceitClient()
        player = None
        try:
            if raw.startswith("7656119"):
                player = client.get_player_by_steam_id(raw)
            else:
                try:
                    player = client.get_player_by_nickname(raw)
                except FaceitError:
                    player = client.get_player(raw)
        except FaceitError as e:
            return Response({"detail": str(e)}, status=404)
        except Exception:
            return Response({"detail": "Faceit не найден"}, status=404)

        if not player:
            return Response({"detail": "Faceit не найден"}, status=404)

        pid = player.get("player_id")
        nick = player.get("nickname") or raw
        steam32 = None
        games = player.get("games") or {}
        cs = games.get("cs2") or games.get("csgo") or {}
        gp = str(cs.get("game_player_id") or "")
        if gp.startswith("7656119"):
            steam32 = steam64_to_32(gp)
        elif raw.startswith("7656119"):
            steam32 = steam64_to_32(raw)

        stats = {}
        try:
            stats = client.get_player_stats(pid, "cs2") or {}
        except Exception:
            pass

        # per-match stats (kills/deaths) если API отдаёт
        per_match = {}
        try:
            recent_stats = client.get_recent_match_stats(pid, "cs2", limit=20) or {}
            items_st = recent_stats.get("items") or []
            if isinstance(recent_stats, list):
                items_st = recent_stats
            for row in items_st:
                if not isinstance(row, dict):
                    continue
                mid = row.get("match_id") or (row.get("stats") or {}).get("match_id")
                st = row.get("stats") or row
                if not mid:
                    continue
                try:
                    k = int(float(str(st.get("Kills") or st.get("kills") or 0)))
                    d = int(float(str(st.get("Deaths") or st.get("deaths") or 0)))
                    a = int(float(str(st.get("Assists") or st.get("assists") or 0)))
                except (TypeError, ValueError):
                    k = d = a = 0
                per_match[str(mid)] = (k, d, a)
        except Exception:
            pass

        history = []
        try:
            hist = client.get_history(pid, game="cs2", limit=20) or {}
            items = hist.get("items") if isinstance(hist, dict) else hist
            if not isinstance(items, list):
                items = []
            for m in items[:20]:
                if not isinstance(m, dict):
                    continue
                mid = m.get("match_id")
                teams = m.get("teams") or {}
                results = m.get("results") or {}
                winner = results.get("winner")
                score = results.get("score") or {}

                # в какой команде был игрок
                my_faction = None
                for fk in ("faction1", "faction2"):
                    roster = (teams.get(fk) or {}).get("players") or (teams.get(fk) or {}).get("roster") or []
                    for p in roster:
                        if not isinstance(p, dict):
                            continue
                        if p.get("player_id") == pid or (p.get("nickname") or "").lower() == (nick or "").lower():
                            my_faction = fk
                            break
                    if my_faction:
                        break

                won = None
                if winner and my_faction:
                    won = str(winner) == str(my_faction)

                s1 = score.get("faction1")
                s2 = score.get("faction2")
                score_str = f"{s1}:{s2}" if s1 is not None and s2 is not None else ""

                kda = per_match.get(str(mid))
                if kda:
                    subtitle = f"{kda[0]}/{kda[1]}/{kda[2]}"
                    if score_str:
                        subtitle = f"{subtitle} · {score_str}"
                else:
                    subtitle = score_str or (m.get("game_mode") or "5v5")

                played_at = None
                ts = m.get("finished_at") or m.get("started_at")
                if ts is not None:
                    try:
                        ts = int(ts)
                        if ts > 10_000_000_000:
                            ts = ts // 1000
                        played_at = datetime.utcfromtimestamp(ts).strftime("%d.%m.%Y")
                    except Exception:
                        played_at = None

                history.append({
                    "won": won,
                    "title": m.get("competition_name") or "Match",
                    "subtitle": subtitle,
                    "match_id": mid,
                    "played_at": played_at,
                })
        except Exception:
            pass

        life = (stats.get("lifetime") or {}) if isinstance(stats, dict) else {}

        def _num(key_list, default=0):
            for k in key_list:
                if k in life and life[k] not in (None, ""):
                    try:
                        return float(str(life[k]).replace("%", "").replace(",", "."))
                    except (TypeError, ValueError):
                        pass
            return default

        wins = int(_num(["Wins", "wins"], 0))
        matches = int(_num(["Matches", "matches"], 0))
        losses = max(matches - wins, 0) if matches else 0
        winrate = round(wins / matches * 100, 1) if matches else 0
        # иногда Faceit отдаёт Win Rate % напрямую
        wr_life = _num(["Win Rate %", "Win Rate", "win_rate"], None)
        if wr_life is not None and matches:
            winrate = round(wr_life, 1)

        elo = (cs.get("faceit_elo") if isinstance(cs, dict) else None) or player.get("faceit_elo")
        level = cs.get("skill_level") if isinstance(cs, dict) else None

        extra = {
            "wins": wins,
            "losses": losses,
            "matches": matches,
            "winrate": winrate,
            "faceit_elo": elo,
            "skill_level": level,
            "match_history": history,
            "lifetime": life,
            "player_id": pid,
        }

        gh = (
            GameAccount.objects.filter(platform="faceit", external_id__iexact=nick)
            .select_related("user")
            .first()
            or GameAccount.objects.filter(platform="faceit", extra_stats__player_id=pid)
            .select_related("user")
            .first()
        )

        related = related_games_for_steam32(steam32, current="faceit") if steam32 else []

        return Response({
            "is_public": True,
            "display_name": nick,
            "avatar_url": player.get("avatar") or None,
            "is_gamehub_user": bool(gh),
            "gamehub_user_id": gh.user_id if gh else None,
            "wins": wins,
            "losses": losses,
            "winrate": winrate,
            "tier": f"Lvl {level} · {elo} ELO" if level is not None else (f"{elo} ELO" if elo else None),
            "skill_rating": elo,
            "match_history": history,
            "related_games": related,
            "empty_reason": None if matches or history else "Нет статистики CS2 на Faceit",
            "display_stats": build_display_stats("faceit", extra),
        })

    

    def _related_games_for_steam32(self, steam32: str, current: str = "dota2"):
        """Чипы других игр для guest (Dota / Deadlock / Faceit / GH)."""
        from django.core.cache import cache

        steam32 = str(steam32 or "").strip()
        if not steam32.isdigit():
            return []

        cache_key = f"related_steam32:{steam32}:v1"
        cached = cache.get(cache_key)
        if cached is not None:
            return [r for r in cached if r.get("game") != current]

        related = []

        related.append({
            "game": "dota2",
            "label": "Dota 2",
            "external_id": steam32,
            "path": f"/players/guest/dota2/{steam32}",
        })
        related.append({
            "game": "deadlock",
            "label": "Deadlock",
            "external_id": steam32,
            "path": f"/players/guest/deadlock/{steam32}",
        })

        try:
            steam64 = str(int(steam32) + 76561197960265728)
            from .integrations.faceit_client import FaceitClient
            p = FaceitClient().get_player_by_steam_id(steam64)
            if p and (p.get("nickname") or p.get("player_id")):
                nick = p.get("nickname") or p.get("player_id")
                related.append({
                    "game": "faceit",
                    "label": "Faceit",
                    "external_id": nick,
                    "path": f"/players/guest/faceit/{nick}",
                })
        except Exception:
            pass

        ga = (
            GameAccount.objects.filter(platform="opendota", external_id=steam32)
            .select_related("user")
            .first()
        )
        if ga and ga.user_id:
            related.insert(0, {
                "game": "gamehub",
                "label": "Профиль GameEyes",
                "external_id": str(ga.user_id),
                "path": f"/players/{ga.user_id}",
            })

        cache.set(cache_key, related, 600)
        return [r for r in related if r.get("game") != current]

    def _dota_guest(self, external_id):
        """Один метод. Пустые данные → 200, не 404. Steam64 → Steam32."""
        from datetime import datetime
        from .integrations.opendota_client import OpenDotaClient
        from .serivces import build_display_stats

        raw = str(external_id or "").strip()
        if not raw:
            return Response({"detail": "Нет id"}, status=400)

        if raw.startswith("7656119"):
            try:
                account_id = str(int(raw) & 0xFFFFFFFF)
            except (TypeError, ValueError):
                account_id = raw
        else:
            account_id = raw

        client = OpenDotaClient()
        player = {}
        wl = {}
        heroes_raw = []
        hero_names = {}
        recent = []
        detail_hint = None

        try:
            player = client.get_player(account_id) or {}
            wl = client.get_win_loss(account_id) or {}
        except Exception:
            detail_hint = "OpenDota не ответил или профиль недоступен"

        try:
            heroes_raw = client.get_heroes(account_id) or []
            hero_names = client.get_hero_names() or {}
        except Exception:
            pass

        try:
            recent = client.get_recent_matches(account_id, limit=30) or []
        except Exception:
            if not detail_hint:
                detail_hint = "История матчей OpenDota недоступна"

        profile = player.get("profile") or {}
        wins = int(wl.get("win") or 0)
        losses = int(wl.get("lose") or 0)
        total = wins + losses
        winrate = round(wins / total * 100, 1) if total else 0
        mmr = (player.get("mmr_estimate") or {}).get("estimate")
        rank_tier = player.get("rank_tier")

        display_name = profile.get("personaname") or f"Player {account_id}"
        avatar_url = profile.get("avatarfull") or profile.get("avatar")

        # Steam fallback для ника/авы
        try:
            from .integrations.steam_client import SteamClient
            sid64 = str(int(account_id) + 76561197960265728)
            rows = SteamClient().get_player_summaries([sid64]) or []
            if rows:
                if rows[0].get("personaname"):
                    display_name = rows[0]["personaname"]
                av = rows[0].get("avatarfull") or rows[0].get("avatarmedium")
                if av:
                    avatar_url = av
        except Exception:
            pass

        top = sorted(heroes_raw, key=lambda h: h.get("games", 0), reverse=True)[:8]
        top_heroes = [
            {
                "name": hero_names.get(h.get("hero_id"), f"Hero {h.get('hero_id')}"),
                "games": h.get("games", 0),
                "winrate": (
                    round(h["win"] / h["games"] * 100, 1) if h.get("games") else 0
                ),
            }
            for h in top
            if h.get("games")
        ]

        match_history = []
        for m in recent[:30]:
            is_radiant = (m.get("player_slot") or 0) < 128
            rw = m.get("radiant_win")
            won = None
            if rw is not None:
                won = bool(rw) if is_radiant else (not bool(rw))
            hid = m.get("hero_id")
            title = hero_names.get(hid, f"Hero {hid}")
            k = m.get("kills", 0)
            d = m.get("deaths", 0)
            a = m.get("assists", 0)
            played_at = None
            if m.get("start_time"):
                try:
                    played_at = datetime.utcfromtimestamp(int(m["start_time"])).strftime("%d.%m.%Y")
                except Exception:
                    pass
            duration = None
            if m.get("duration") is not None:
                try:
                    sec = int(m["duration"])
                    duration = f"{sec // 60}:{sec % 60:02d}"
                except Exception:
                    pass
            match_history.append({
                "won": won,
                "title": title,
                "subtitle": f"{k}/{d}/{a}",
                "match_id": m.get("match_id"),
                "played_at": played_at,
                "duration": duration,
            })

        if total == 0 and not match_history and not detail_hint:
            detail_hint = (
                "Нет публичных матчей OpenDota "
                "(профиль Steam может быть скрыт) или почти нет каток."
            )

        extra = {
            "wins": wins,
            "losses": losses,
            "matches": total,
            "total_matches": total,
            "winrate": winrate,
            "mmr_estimate": mmr,
            "rank_tier": rank_tier,
            "top_heroes": top_heroes,
            "match_history": match_history,
        }

        gh = (
            GameAccount.objects.filter(platform="opendota", external_id=str(account_id))
            .select_related("user", "user__profile")
            .first()
        )

        related = self._related_games_for_steam32(account_id, current="dota2")
        is_empty = wins == 0 and losses == 0 and not match_history

        return Response(
            {
                "is_public": True,
                "platform": "opendota",
                "game": "dota2",
                "external_id": account_id,
                "display_name": display_name,
                "avatar_url": avatar_url,
                "is_gamehub_user": bool(gh),
                "gamehub_user_id": gh.user_id if gh else None,
                "wins": wins,
                "losses": losses,
                "winrate": winrate,
                "mmr_estimate": mmr,
                "rank_tier": rank_tier,
                "tier": None,
                "top_heroes": top_heroes,
                "match_history": match_history,
                "related_games": related,
                "display_stats": build_display_stats("opendota", extra),
                "is_empty": is_empty,
                "detail_hint": detail_hint,
                "empty_reason": detail_hint if is_empty else None,
            },
            status=200,
        )

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
    permission_classes = [permissions.AllowAny]

    def get(self, request, game, match_id):
        game = (game or "").lower()
        if game in ("opendota", "dota"):
            game = "dota2"
        if game == "dota2":
            return self._dota_participants(match_id)
        if game == "valorant":
            return self._valorant_participants(match_id)
        if game == "faceit":
            return self._faceit_participants(match_id)
        if game in ("faceit", "cs2"):
            return self._faceit_participants(match_id)
        if game == "deadlock":
            return self._deadlock_participants(match_id)
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

    def _deadlock_participants(self, match_id):
        import requests
        from django.conf import settings
        from django.core.cache import cache
        from .models import GameAccount

        base = "https://api.deadlock-api.com"
        headers = {"Accept": "application/json"}
        key = getattr(settings, "DEADLOCK_API_KEY", "") or ""
        if key:
            headers["X-API-Key"] = key

        try:
            r = requests.get(
                f"{base}/v1/matches/{match_id}/metadata",
                headers=headers,
                timeout=20,
            )
            if r.status_code != 200:
                return Response(
                    {"detail": f"Матч не найден ({r.status_code})"},
                    status=404,
                )
            detail = r.json()
        except Exception:
            return Response({"detail": "Матч Deadlock не найден"}, status=404)

        if not isinstance(detail, dict):
            return Response({"detail": "Матч Deadlock не найден"}, status=404)

        match_info = detail.get("match_info") or {}
        if not isinstance(match_info, dict):
            match_info = {}

        players = match_info.get("players") or detail.get("players") or []
        if not isinstance(players, list):
            players = []

        duration = match_info.get("duration_s") or detail.get("duration_s")
        winning_team = match_info.get("winning_team")
        if winning_team is None:
            winning_team = match_info.get("match_outcome")

        # --- имена героев (ключи только str) ---
        hero_names = cache.get("deadlock:hero_names") or {}
        # нормализуем старый кэш с int-ключами
        if hero_names and any(not isinstance(k, str) for k in hero_names.keys()):
            hero_names = {str(k): v for k, v in hero_names.items()}
            cache.set("deadlock:hero_names", hero_names, 3600)

        if not hero_names:
            try:
                from .integrations.deadlock_client import DeadlockClient
                heroes = DeadlockClient().get_heroes() or []
                if isinstance(heroes, dict):
                    heroes = heroes.get("heroes") or heroes.get("data") or []
                if isinstance(heroes, list):
                    hero_names = {}
                    for h in heroes:
                        if not isinstance(h, dict):
                            continue
                        hid = h.get("id")
                        if hid is None:
                            hid = h.get("hero_id")
                        if hid is None:
                            continue
                        name = (
                            h.get("name")
                            or h.get("display_name")
                            or h.get("class_name")
                            or h.get("localized_name")
                        )
                        if name:
                            name = str(name).replace("hero_", "").replace("_", " ").title()
                            hero_names[str(hid)] = name
                    if hero_names:
                        cache.set("deadlock:hero_names", hero_names, 3600)
            except Exception:
                hero_names = {}

        participants = []
        for p in players:
            if not isinstance(p, dict):
                continue

            account_id = p.get("account_id")
            if account_id is not None:
                try:
                    account_id = str(int(account_id) & 0xFFFFFFFF)
                except (TypeError, ValueError):
                    account_id = str(account_id)

            hid = p.get("hero_id")
            hero = hero_names.get(str(hid), f"Hero {hid}" if hid is not None else "?")

            kills = p.get("player_kills", p.get("kills", 0)) or 0
            deaths = p.get("player_deaths", p.get("deaths", 0)) or 0
            assists = p.get("player_assists", p.get("assists", 0)) or 0

            team = p.get("player_team", p.get("team"))
            try:
                team = int(team) if team is not None else None
            except (TypeError, ValueError):
                team = None

            gh = None
            if account_id:
                gh = (
                    GameAccount.objects.filter(
                        platform="deadlock",
                        external_id=str(account_id),
                    )
                    .select_related("user")
                    .first()
                )

            participants.append({
                "account_id": account_id,
                "display_name": (
                    (gh.nickname if gh else None)
                    or p.get("name")
                    or (f"Player {account_id}" if account_id else "?")
                ),
                "avatar": None,
                "hero": hero,
                "level": p.get("hero_level") or p.get("level"),
                "kda": f"{kills}/{deaths}/{assists}",
                "net_worth": p.get("net_worth"),
                "team": team,
                "is_team0": team == 0,
                "is_gamehub_user": bool(gh),
                "gamehub_user_id": gh.user_id if gh else None,
            })

        # --- Steam ники + аватарки ---
        steam_ids = []
        for p in participants:
            aid = p.get("account_id")
            if not aid:
                continue
            try:
                steam_ids.append(str(int(aid) + 76561197960265728))
            except (TypeError, ValueError):
                pass

        personas = {}
        if steam_ids:
            try:
                from .integrations.steam_client import SteamClient
                sc = SteamClient()
                for i in range(0, len(steam_ids), 100):
                    chunk = steam_ids[i:i + 100]
                    for row in (sc.get_player_summaries(chunk) or []):
                        sid = str(row.get("steamid") or "")
                        if sid:
                            personas[sid] = row
            except Exception:
                personas = {}

        for p in participants:
            aid = p.get("account_id")
            if not aid:
                continue
            try:
                sid64 = str(int(aid) + 76561197960265728)
            except (TypeError, ValueError):
                continue
            row = personas.get(sid64) or {}
            if row.get("personaname"):
                p["display_name"] = row["personaname"]
            av = row.get("avatarfull") or row.get("avatarmedium") or row.get("avatar")
            if av:
                p["avatar"] = av

        return Response({
            "participants": participants,
            "duration": duration,
            "winning_team": winning_team,
            "map": "Deadlock",
        })


    def _faceit_participants(self, match_id):
        from .integrations.faceit_client import FaceitClient, FaceitError
        from .models import GameAccount

        client = FaceitClient()
        try:
            detail = client.get_match(match_id)
        except FaceitError as e:
            return Response({"detail": str(e)}, status=404)
        except Exception:
            return Response({"detail": "Матч не найден"}, status=404)

        teams = detail.get("teams") or {}
        f1 = teams.get("faction1") or {}
        f2 = teams.get("faction2") or {}
        results = detail.get("results") or {}
        score = results.get("score") or {}

        # per-player stats from /matches/{id}/stats
        per_player = {}
        try:
            stats_payload = client.get_match_stats(match_id)
            for rnd in (stats_payload.get("rounds") or []):
                for team in (rnd.get("teams") or []):
                    for p in (team.get("players") or []):
                        pid = p.get("player_id")
                        if not pid:
                            continue
                        st = p.get("player_stats") or {}
                        if pid not in per_player:
                            per_player[pid] = {
                                "kills": 0, "deaths": 0, "assists": 0,
                                "headshots": 0, "mvps": 0,
                            }
                        per_player[pid]["kills"] += int(st.get("Kills") or st.get("kills") or 0)
                        per_player[pid]["deaths"] += int(st.get("Deaths") or st.get("deaths") or 0)
                        per_player[pid]["assists"] += int(st.get("Assists") or st.get("assists") or 0)
                        per_player[pid]["headshots"] += int(
                            st.get("Headshots") or st.get("headshots") or 0
                        )
                        per_player[pid]["mvps"] += int(st.get("MVPs") or st.get("mvps") or 0)
        except Exception:
            pass

        def pack_roster(roster, team_key):
            out = []
            for p in roster or []:
                pid = p.get("player_id")
                nick = p.get("nickname") or "?"
                st = per_player.get(pid) or {}
                k = st.get("kills", 0)
                d = st.get("deaths", 0)
                a = st.get("assists", 0)

                gh = GameAccount.objects.filter(
                    platform="faceit",
                    external_id__iexact=nick,
                ).select_related("user").first()
                if not gh and pid:
                    gh = GameAccount.objects.filter(
                        platform="faceit",
                        extra_stats__player_id=pid,
                    ).select_related("user").first()

                out.append({
                    "player_id": pid,
                    "nickname": nick,
                    "display_name": nick,
                    "avatar": p.get("avatar"),
                    "team": team_key,
                    "kda": f"{k}/{d}/{a}",
                    "headshots": st.get("headshots", 0),
                    "mvps": st.get("mvps", 0),
                    "is_gamehub_user": bool(gh),
                    "gamehub_user_id": gh.user_id if gh else None,
                })
            return out

        participants = (
            pack_roster(f1.get("roster") or f1.get("players"), "faction1")
            + pack_roster(f2.get("roster") or f2.get("players"), "faction2")
        )

        map_name = None
        voting = detail.get("voting") or {}
        if isinstance(voting.get("map"), dict):
            map_name = (voting["map"].get("pick") or [None])[0]
        map_name = map_name or detail.get("map") or (detail.get("entity") or {}).get("name")

        return Response({
            "participants": participants,
            "map": map_name,
            "faction1_name": f1.get("name") or "Team 1",
            "faction2_name": f2.get("name") or "Team 2",
            "faction1_score": score.get("faction1"),
            "faction2_score": score.get("faction2"),
            "winner": results.get("winner"),
            "competition": (detail.get("competition_name") or detail.get("competition") or ""),
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
  