from django.db.models import OuterRef, Subquery

from apps.profiles.models import DailySnapshot
from .models import Clan, ClanMembership

# Steam appids
GAME_APPIDS = {
    "dota2": 570,
    "cs2": 730,
    "deadlock": 1422450,
}


def get_users_playtime(user_ids):
    user_ids = list(user_ids)
    if not user_ids:
        return {}

    newest_date = (
        DailySnapshot.objects.filter(
            game_account=OuterRef("game_account"),
            appid=OuterRef("appid"),
        )
        .order_by("-date")
        .values("date")[:1]
    )
    rows = DailySnapshot.objects.filter(
        game_account__user_id__in=user_ids,
        game_account__platform="steam",
        date=Subquery(newest_date),
    ).values_list(
        "game_account__user_id",
        "appid",
        "playtime_forever",
        "playtime_2weeks",
    )

    best = {}
    for uid, appid, forever, two_weeks in rows:
        forever = forever or 0
        two_weeks = two_weeks or 0
        cur = best.get((uid, appid))
        if cur is None:
            best[(uid, appid)] = [forever, two_weeks]
        else:
            cur[0] = max(cur[0], forever)
            cur[1] = max(cur[1], two_weeks)

    result = {}
    for (uid, _appid), (forever, two_weeks) in best.items():
        r = result.setdefault(uid, {"two_weeks": 0, "total": 0})
        r["two_weeks"] += two_weeks
        r["total"] += forever
    return result


def get_clan_dashboard(clan: Clan):
    memberships = list(
        ClanMembership.objects.filter(clan=clan).select_related("user")
    )
    stats = get_users_playtime([m.user_id for m in memberships])
    result = []
    for m in memberships:
        s = stats.get(m.user_id, {"two_weeks": 0, "total": 0})
        result.append({
            "user_id": m.user_id,
            "username": m.user.username,
            "role": m.role,
            "joined_at": m.joined_at,
            "two_weeks_playtime": s["two_weeks"],
            "total_playtime": s["total"],
            "is_inactive": s["two_weeks"] == 0,
        })
    result.sort(key=lambda x: (-x["two_weeks_playtime"], -x["total_playtime"]))
    return result


def get_user_game_hours(user_id, game: str) -> float:
    """Часы в игре клана. Для multi/other порог не режем снаружи."""
    game = (game or "").lower()
    if game in ("multigaming", "other", ""):
        return 999999.0

    appid = GAME_APPIDS.get(game)
    if appid:
        row = (
            DailySnapshot.objects.filter(
                game_account__user_id=user_id,
                game_account__platform="steam",
                appid=appid,
            )
            .order_by("-date")
            .values("playtime_forever")
            .first()
        )
        if row and row.get("playtime_forever") is not None:
            return round((row["playtime_forever"] or 0) / 60.0, 1)
        return 0.0

    platform_map = {
        "valorant": "valorant",
        "lol": "lol",
        "cs2": "faceit",
    }
    plat = platform_map.get(game)
    if not plat:
        return 0.0

    from apps.profiles.models import GameAccount

    acc = (
        GameAccount.objects.filter(user_id=user_id, platform=plat)
        .order_by("-last_synced_at")
        .first()
    )
    if not acc:
        return 0.0
    es = acc.extra_stats or {}
    if es.get("hours_played") is not None:
        try:
            return float(es["hours_played"])
        except (TypeError, ValueError):
            pass
    if getattr(acc, "verified", False) or acc.last_synced_at:
        return 999999.0
    return 0.0


def _check_join_allowed(clan: Clan, user) -> None:
    if ClanMembership.objects.filter(clan=clan, user=user).exists():
        raise ValueError("Ты уже состоишь в этом клане")

    count = clan.memberships.count()
    if clan.max_members is not None and count >= clan.max_members:
        raise ValueError("Клан заполнен")

    need = getattr(clan, "min_playtime_hours", None)
    game = getattr(clan, "game", None) or "multigaming"
    if need is not None and need > 0 and game not in ("multigaming", "other"):
        have = get_user_game_hours(user.id, game)
        if have < need:
            choices = dict(getattr(Clan, "GAME_CHOICES", []) or [])
            label = choices.get(game, game)
            raise ValueError(
                f"Нужно минимум {need} ч. в {label} (у тебя ~{have} ч.)"
            )


def _after_join(clan, user, membership):
    try:
        from apps.profiles.models import ClanActivity

        ClanActivity.objects.create(
            clan=clan,
            user=user,
            kind="joined",
            text=f"{user.username} вступил в клан",
        )
    except Exception:
        pass
    try:
        from apps.users.services import notify
        from apps.users.xp import add_xp, XP_CLAN_JOIN

        if clan.owner_id != user.id:
            notify(
                clan.owner,
                kind="clan_join",
                title="Новый участник",
                body=f"{user.username} вступил в {clan.name}",
                link="/clans",
            )
        add_xp(user, XP_CLAN_JOIN, reason="вступление в клан")
    except Exception:
        pass
    return membership


def join_clan_by_invite_code(user, invite_code: str) -> ClanMembership:
    code = (invite_code or "").strip().upper()
    try:
        clan = Clan.objects.get(invite_code__iexact=code)
    except Clan.DoesNotExist:
        raise ValueError("Неверный код приглашения")

    _check_join_allowed(clan, user)
    membership = ClanMembership.objects.create(clan=clan, user=user, role="member")
    return _after_join(clan, user, membership)


def join_open_clan(user, clan_id: int) -> ClanMembership:
    try:
        clan = Clan.objects.get(pk=clan_id)
    except Clan.DoesNotExist:
        raise ValueError("Клан не найден")

    if not getattr(clan, "is_open", False):
        raise ValueError("Клан закрытый — нужен код приглашения")

    _check_join_allowed(clan, user)
    membership = ClanMembership.objects.create(clan=clan, user=user, role="member")
    return _after_join(clan, user, membership)
