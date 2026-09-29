from datetime import datetime, timedelta
from collections import Counter

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions, status
from .models import GameAccount, FavoritePlayer, ClanActivity
from .models import FavoritePlayer

User = get_user_model()

WEEKLY_GAMES = {
    "opendota": {"key": "dota2", "label": "Dota 2"},
    "dota2": {"key": "dota2", "label": "Dota 2"},
    "valorant": {"key": "valorant", "label": "Valorant"},
}

GAME_META = {
    "opendota": {"key": "dota2", "label": "Dota 2"},
    "dota2": {"key": "dota2", "label": "Dota 2"},
    "valorant": {"key": "valorant", "label": "Valorant"},
    "faceit": {"key": "cs2", "label": "CS2"},
    "steam": {"key": "steam", "label": "Steam"},
}


def _primary_account(user, platforms=("opendota", "valorant", "faceit", "lol")):
    return (
        GameAccount.objects.filter(user=user, verified=True, platform__in=platforms)
        .exclude(extra_stats__isnull=True)
        .order_by("-last_synced_at")
        .first()
    )


def _stats_from_account(acc):
    if not acc:
        return None
    es = acc.extra_stats or {}
    history = es.get("match_history") or []
    wins = sum(1 for m in history if m.get("won") is True)
    losses = sum(1 for m in history if m.get("won") is False)
    total = wins + losses
    titles = [m.get("title") for m in history if m.get("title")]
    top = Counter(titles).most_common(3)
    return {
        "platform": acc.platform,
        "game_label": acc.game_label or acc.platform,
        "wins": wins,
        "losses": losses,
        "winrate": round(wins / total * 100, 1) if total else 0,
        "matches_sample": total,
        "top_heroes": [{"name": n, "games": c} for n, c in top],
        "skill_rating": acc.skill_rating,
        "recent": history[:5],
    }


def _parse_played(s):
    if not s:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def _parse_match_date(m):
    """played_at вида 24.08.2026 или ISO — вернуть date или None"""
    raw = m.get("played_at") or m.get("date")
    if not raw:
        return None
    from datetime import datetime
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(raw)[:10], fmt).date()
        except ValueError:
            continue
    return None

class ComparePlayersView(APIView):
    """
    GET /api/players/compare/?user_id=2
    GET /api/players/compare/?platform=opendota&external_id=123
    GET /api/players/compare/?user_id=2&game=dota2
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        uid = request.query_params.get("user_id")
        platform = (request.query_params.get("platform") or "").strip().lower()
        external_id = str(request.query_params.get("external_id") or "").strip()
        game_filter = (request.query_params.get("game") or "").strip().lower()
        if game_filter in ("opendota", "dota"):
            game_filter = "dota2"

        me_block = self._user_block(request.user)

        if uid:
            try:
                other_user = User.objects.get(id=int(uid))
            except (User.DoesNotExist, ValueError, TypeError):
                return Response({"detail": "Игрок не найден"}, status=404)
            other_block = self._user_block(other_user)
        elif platform and external_id:
            if platform in ("dota2", "dota"):
                platform = "opendota"
            other_block = self._guest_block(platform, external_id)
        else:
            return Response(
                {"detail": "Нужен user_id или platform + external_id"},
                status=400,
            )

        # общие игры (пересечение ключей), плюс гость = одна игра
        me_keys = {g["key"] for g in me_block["games"]}
        other_keys = {g["key"] for g in other_block["games"]}
        common = sorted(me_keys & other_keys)
        all_keys = sorted(me_keys | other_keys)

        available = []
        for k in all_keys:
            label = next(
                (g["label"] for g in me_block["games"] + other_block["games"] if g["key"] == k),
                k,
            )
            available.append({
                "value": k,
                "label": label,
                "common": k in common,
            })

        # дефолт: первая общая, иначе первая у me, иначе dota2
        if not game_filter:
            if common:
                game_filter = common[0]
            elif me_keys:
                game_filter = next(iter(me_keys))
            elif other_keys:
                game_filter = next(iter(other_keys))
            else:
                game_filter = "dota2"

        me_game = next((g for g in me_block["games"] if g["key"] == game_filter), None)
        other_game = next((g for g in other_block["games"] if g["key"] == game_filter), None)

        return Response({
            "game": game_filter,
            "available_games": available,
            "me": {
                "kind": me_block["kind"],
                "display_name": me_block["display_name"],
                "username": me_block["username"],
                "avatar_url": me_block["avatar_url"],
                "stats": me_game,
            },
            "other": {
                "kind": other_block["kind"],
                "display_name": other_block["display_name"],
                "username": other_block.get("username"),
                "avatar_url": other_block["avatar_url"],
                "stats": other_game,
            },
            "diff": self._diff(me_game, other_game),
        })

    def _user_block(self, user):
        profile = getattr(user, "profile", None)
        accounts = GameAccount.objects.filter(user=user).exclude(extra_stats__isnull=True)
        games = []
        for acc in accounts:
            meta = GAME_META.get(acc.platform)
            if not meta:
                continue
            games.append(self._from_account(acc, meta))
        return {
            "kind": "user",
            "display_name": (profile.display_name if profile and profile.display_name else user.username),
            "username": user.username,
            "avatar_url": profile.avatar_url if profile else None,
            "games": games,
        }

    def _from_account(self, acc, meta):
        s = acc.extra_stats or {}
        history = s.get("match_history") or []

        wins = s.get("wins")
        losses = s.get("losses")
        if wins is None:
            wins = s.get("matches_won") or 0
        if losses is None:
            losses = 0
        if not wins and not losses and history:
            wins = sum(1 for m in history if m.get("won") is True)
            losses = sum(1 for m in history if m.get("won") is False)

        total = (wins or 0) + (losses or 0)
        winrate = round(wins / total * 100, 1) if total else 0

        # KDA по истории
        k_sum = d_sum = a_sum = 0
        kda_n = 0
        for m in history[:30]:
            sub = m.get("subtitle") or ""
            parts = sub.replace(" ", "").split("/")
            if len(parts) >= 3:
                try:
                    k_sum += int(parts[0])
                    d_sum += int(parts[1])
                    a_sum += int(parts[2])
                    kda_n += 1
                except ValueError:
                    pass
        avg_kda = None
        if kda_n:
            avg_k = round(k_sum / kda_n, 1)
            avg_d = round(d_sum / kda_n, 1)
            avg_a = round(a_sum / kda_n, 1)
            ratio = round((k_sum + a_sum) / max(d_sum, 1), 2)
            avg_kda = f"{avg_k}/{avg_d}/{avg_a} ({ratio})"

        c = Counter()
        for m in history[:40]:
            if m.get("title"):
                c[m["title"]] += 1
        top_heroes = [{"name": n, "games": g} for n, g in c.most_common(8)]

        # verdicts
        verdicts = Counter()
        for m in history[:30]:
            v = (m.get("verdict") or {}).get("label")
            if v:
                verdicts[v] += 1

        recent_form = []
        for m in history[:10]:
            if m.get("won") is True:
                recent_form.append("W")
            elif m.get("won") is False:
                recent_form.append("L")

        streak = 0
        for m in history:
            if m.get("won") is True:
                streak += 1
            else:
                break

        return {
            "key": meta["key"],
            "label": meta["label"],
            "platform": acc.platform,
            "game_label": acc.game_label or meta["label"],
            "nickname": acc.nickname,
            "skill_rating": acc.skill_rating,
            "tier": s.get("tier") or s.get("rank"),
            "rr": s.get("rr"),
            "wins": wins or 0,
            "losses": losses or 0,
            "matches": total,
            "winrate": winrate,
            "avg_kda": avg_kda,
            "main_agent": s.get("main_agent"),
            "top_heroes": top_heroes,
            "verdicts": [{"label": k, "count": v} for k, v in verdicts.most_common(5)],
            "recent_form": recent_form,
            "win_streak": streak,
            "extra": {
                k: s.get(k)
                for k in ("mmr", "rank_tier", "hours_played", "kd", "headshot_pct")
                if s.get(k) is not None
            },
        }

    def _guest_block(self, platform, external_id):
        meta = GAME_META.get(platform) or {"key": platform, "label": platform}
        if platform == "opendota":
            game = self._opendota_guest_stats(external_id, meta)
            avatar = game.pop("_avatar", None)
            name = game.pop("_name", external_id)
            return {
                "kind": "guest",
                "display_name": name,
                "username": None,
                "avatar_url": avatar,
                "games": [game],
            }
        return {
            "kind": "guest",
            "display_name": external_id,
            "username": None,
            "avatar_url": None,
            "games": [{
                "key": meta["key"],
                "label": meta["label"],
                "platform": platform,
                "game_label": meta["label"],
                "wins": 0,
                "losses": 0,
                "matches": 0,
                "winrate": 0,
                "top_heroes": [],
                "recent_form": [],
                "verdicts": [],
            }],
        }

    def _opendota_guest_stats(self, external_id, meta):
        from .integrations.opendota_client import OpenDotaClient

        client = OpenDotaClient()
        try:
            player = client.get_player(external_id)
            wl = client.get_win_loss(external_id)
            heroes_raw = client.get_heroes(external_id)
            hero_names = client.get_hero_names()
            recent = client.get_recent_matches(external_id, limit=20)
        except Exception:
            return {
                "key": meta["key"],
                "label": meta["label"],
                "platform": "opendota",
                "game_label": "Dota 2",
                "wins": 0,
                "losses": 0,
                "matches": 0,
                "winrate": 0,
                "avg_kda": None,
                "top_heroes": [],
                "recent_form": [],
                "verdicts": [],
                "win_streak": 0,
                "extra": {},
                "_avatar": None,
                "_name": external_id,
            }

        wins = wl.get("win", 0)
        losses = wl.get("lose", 0)
        total = wins + losses

        top = sorted(
            heroes_raw or [],
            key=lambda h: h.get("games", 0),
            reverse=True,
        )[:8]
        top_heroes = [
            {
                "name": hero_names.get(h["hero_id"], "?"),
                "games": h.get("games", 0),
            }
            for h in top
            if h.get("games")
        ]

        form = []
        k_sum = d_sum = a_sum = n = 0
        for m in recent or []:
            is_radiant = m.get("player_slot", 0) < 128
            won = (is_radiant and m.get("radiant_win")) or (
                not is_radiant and not m.get("radiant_win")
            )
            form.append("W" if won else "L")
            try:
                k_sum += int(m.get("kills") or 0)
                d_sum += int(m.get("deaths") or 0)
                a_sum += int(m.get("assists") or 0)
                n += 1
            except (TypeError, ValueError):
                pass

        avg_kda = None
        if n:
            ratio = round((k_sum + a_sum) / max(d_sum, 1), 2)
            avg_kda = (
                f"{round(k_sum / n, 1)}/{round(d_sum / n, 1)}/{round(a_sum / n, 1)} ({ratio})"
            )

        streak = 0
        for c in form:
            if c == "W":
                streak += 1
            else:
                break

        profile = player.get("profile") or {}
        mmr = (player.get("mmr_estimate") or {}).get("estimate")

        return {
            "key": meta["key"],
            "label": meta["label"],
            "platform": "opendota",
            "game_label": "Dota 2",
            "skill_rating": mmr,
            "wins": wins,
            "losses": losses,
            "matches": total,
            "winrate": round(wins / total * 100, 1) if total else 0,
            "avg_kda": avg_kda,
            "top_heroes": top_heroes,
            "recent_form": form[:10],
            "verdicts": [],
            "win_streak": streak,
            "extra": {
                "mmr": mmr,
                "rank_tier": player.get("rank_tier"),
            },
            "_avatar": profile.get("avatarfull"),
            "_name": profile.get("personaname") or external_id,
        }

    def _diff(self, a, b):
        if not a or not b:
            return None
        return {
            "winrate": round((a.get("winrate") or 0) - (b.get("winrate") or 0), 1),
            "wins": (a.get("wins") or 0) - (b.get("wins") or 0),
            "matches": (a.get("matches") or 0) - (b.get("matches") or 0),
        }


class WeeklyReportView(APIView):
    """
    GET /api/me/weekly-report/?game=dota2|valorant|all
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        game_filter = (request.query_params.get("game") or "all").lower()
        if game_filter in ("opendota", "dota"):
            game_filter = "dota2"

        today = timezone.now().date()
        week_start = today - timedelta(days=6)

        accounts = GameAccount.objects.filter(user=request.user)
        available = []
        seen_keys = set()

        wins = losses = 0
        hero_counter = Counter()
        streak_wins = 0
        counting_streak = True

        all_week_matches = []  # (date, won, title) для серии

        for acc in accounts:
            meta = WEEKLY_GAMES.get(acc.platform)
            if not meta:
                continue
            if meta["key"] not in seen_keys:
                seen_keys.add(meta["key"])
                available.append({"value": meta["key"], "label": meta["label"]})

            if game_filter != "all" and meta["key"] != game_filter:
                continue

            stats = acc.extra_stats or {}
            history = stats.get("match_history") or []
            for m in history:
                d = _parse_match_date(m)
                if d is None or d < week_start or d > today:
                    continue
                won = m.get("won")
                if won is True:
                    wins += 1
                elif won is False:
                    losses += 1
                title = m.get("title") or "?"
                if title:
                    hero_counter[title] += 1
                all_week_matches.append((d, won, title))

        # серия побед с конца (новые матчи первые в history — пересортируем по дате)
        all_week_matches.sort(key=lambda x: x[0], reverse=True)
        for _, won, _ in all_week_matches:
            if won is True and counting_streak:
                streak_wins += 1
            else:
                counting_streak = False

        best = hero_counter.most_common(1)
        best_hero = best[0][0] if best else None

        return Response({
            "period": f"{week_start.strftime('%d.%m')} – {today.strftime('%d.%m')}",
            "game": game_filter,
            "available_games": available,
            "wins": wins,
            "losses": losses,
            "best_hero": best_hero,
            "streak_wins": streak_wins,
        })

class TeammateRecommendationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.lfg.models import LFGPost

        my = _primary_account(request.user)
        my_sr = (my.skill_rating or 0) if my else 0
        my_plat = my.platform if my else None

        qs = (
            GameAccount.objects.filter(verified=True)
            .exclude(user=request.user)
            .select_related("user")
            .order_by("-last_synced_at")[:50]
        )
        open_lfg = set(
            LFGPost.objects.filter(status="open").values_list("author_id", flat=True)
        )

        out, seen = [], set()
        for acc in qs:
            if acc.user_id in seen:
                continue
            seen.add(acc.user_id)
            if my_plat and acc.platform != my_plat:
                continue
            sr = acc.skill_rating or 0
            if my_sr and sr and abs(sr - my_sr) > 1500:
                continue
            p = getattr(acc.user, "profile", None)
            out.append({
                "user_id": acc.user_id,
                "username": acc.user.username,
                "display_name": p.display_name if p else acc.user.username,
                "avatar_url": getattr(p, "avatar_url", None) if p else None,
                "platform": acc.platform,
                "game_label": acc.game_label,
                "skill_rating": sr or None,
                "has_open_lfg": acc.user_id in open_lfg,
                "last_synced_at": acc.last_synced_at,
            })
            if len(out) >= 8:
                break
        return Response(out)


class FavoriteToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        uid_raw = request.data.get("user_id", None)
        platform = (request.data.get("platform") or "").strip().lower()
        external_id = str(request.data.get("external_id") or "").strip()

        # --- пользователь сайта ---
        if uid_raw is not None and uid_raw != "":
            try:
                uid = int(uid_raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "Некорректный user_id"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if uid == request.user.id:
                return Response(
                    {"detail": "Нельзя добавить себя"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not User.objects.filter(id=uid).exists():
                return Response(
                    {"detail": "Пользователь не найден"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            fav = FavoritePlayer.objects.filter(
                owner=request.user, target_user_id=uid
            ).first()
            if fav:
                fav.delete()
                return Response({"favorited": False})
            FavoritePlayer.objects.create(owner=request.user, target_user_id=uid)
            return Response({"favorited": True})

        # --- гость (OpenDota / Valorant / …) ---
        if platform and external_id:
            if platform in ("dota2", "dota"):
                platform = "opendota"
            fav = FavoritePlayer.objects.filter(
                owner=request.user,
                platform=platform,
                external_id=external_id,
            ).first()
            if fav:
                fav.delete()
                return Response({"favorited": False})
            FavoritePlayer.objects.create(
                owner=request.user,
                platform=platform,
                external_id=external_id,
                display_name=(request.data.get("display_name") or external_id)[:128],
                avatar_url=(request.data.get("avatar_url") or "")[:500],
            )
            return Response({"favorited": True})

        return Response(
            {"detail": "Нужен user_id или platform + external_id"},
            status=status.HTTP_400_BAD_REQUEST,
        )


class FavoriteListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rows = (
            FavoritePlayer.objects
            .filter(owner=request.user)
            .select_related("target_user")
            .order_by("-created_at")
        )
        out = []
        for f in rows:
            if f.target_user_id:
                user = f.target_user
                profile = getattr(user, "profile", None)
                out.append({
                    "kind": "user",
                    "user_id": user.id,
                    "display_name": getattr(profile, "display_name", None) or user.username,
                    "avatar_url": getattr(profile, "avatar_url", None),
                    "link": f"/players/{user.id}",
                })
            else:
                g = "dota2" if f.platform == "opendota" else f.platform
                out.append({
                    "kind": "guest",
                    "platform": f.platform,
                    "external_id": f.external_id,
                    "display_name": f.display_name or f.external_id,
                    "avatar_url": f.avatar_url or None,
                    "link": f"/players/guest/{g}/{f.external_id}",
                })
        return Response(out)


class FavoriteStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        uid = request.query_params.get("user_id")
        platform = (request.query_params.get("platform") or "").strip().lower()
        external_id = str(request.query_params.get("external_id") or "").strip()

        if uid:
            try:
                uid = int(uid)
            except ValueError:
                return Response({"favorited": False})
            ok = FavoritePlayer.objects.filter(
                owner=request.user, target_user_id=uid
            ).exists()
            return Response({"favorited": ok})

        if platform in ("dota2", "dota"):
            platform = "opendota"
        if platform and external_id:
            ok = FavoritePlayer.objects.filter(
                owner=request.user,
                platform=platform,
                external_id=external_id,
            ).exists()
            return Response({"favorited": ok})

        return Response({"favorited": False})

class ClanFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, clan_id):
        items = (
            ClanActivity.objects.filter(clan_id=clan_id)
            .select_related("user")[:30]
        )
        return Response([
            {
                "id": a.id,
                "username": a.user.username,
                "kind": a.kind,
                "text": a.text,
                "created_at": a.created_at,
            }
            for a in items
        ])