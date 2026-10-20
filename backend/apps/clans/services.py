from collections import defaultdict
from datetime import timedelta

from django.db.models import Max
from django.utils import timezone as dj_timezone

from .models import Clan, ClanMembership, ClanBan
from apps.profiles.models import DailySnapshot, GameAccount
from apps.users.display import user_public_name

GAME_APPIDS = {
    "dota2": 570,
    "cs2": 730,
    "deadlock": 1422450,
}


def _assert_not_banned(clan, user):
    if ClanBan.objects.filter(clan=clan, user=user).exists():
        raise ValueError("Ты забанен в этом клане")


def get_users_playtime(user_ids):
    """
    Минуты для дашборда клана.
    total     = sum(playtime_forever) по последнему снапшоту каждой игры
    two_weeks = sum(playtime_2weeks)  — как Steam / профиль (не дельта дат)
    Fallback на дельту дат, если playtime_2weeks нигде не заполнен.
    """
    user_ids = list(user_ids or [])
    result = {uid: {"two_weeks": 0, "total": 0} for uid in user_ids}
    if not user_ids:
        return result

    latest = (
        DailySnapshot.objects.filter(game_account__user_id__in=user_ids)
        .values("game_account__user_id", "appid")
        .annotate(max_date=Max("date"))
    )
    date_map = {
        (r["game_account__user_id"], r["appid"]): r["max_date"]
        for r in latest
    }
    if not date_map:
        return result


    from django.db.models import Q
    q = Q()
    for (uid, appid), d in date_map.items():
        q |= Q(game_account__user_id=uid, appid=appid, date=d)

    snaps = (
        DailySnapshot.objects.filter(q)
        .select_related("game_account")
    )

    used_2w = False
    for s in snaps:
        uid = s.game_account.user_id
        if uid not in result:
            continue
        forever = int(s.playtime_forever or 0)
        result[uid]["total"] += max(forever, 0)

        if s.playtime_2weeks is not None:
            result[uid]["two_weeks"] += max(int(s.playtime_2weeks or 0), 0)
            used_2w = True

    if not used_2w:
        today = dj_timezone.now().date()
        two_weeks_ago = today - timedelta(days=14)
        all_snaps = (
            DailySnapshot.objects.filter(game_account__user_id__in=user_ids)
            .select_related("game_account")
            .order_by("date")
        )
        by_key = defaultdict(list)
        for s in all_snaps:
            by_key[(s.game_account.user_id, s.appid)].append(
                (s.date, s.playtime_forever or 0)
            )
        for (uid, _appid), pts in by_key.items():
            if uid not in result:
                continue
            baseline = None
            in_period = []
            for d, val in pts:
                if d < two_weeks_ago:
                    baseline = val
                elif d <= today:
                    in_period.append(val)
            if not in_period:
                continue
            base = baseline if baseline is not None else in_period[0]
            result[uid]["two_weeks"] += max(in_period[-1] - base, 0)

    return result


def get_user_game_hours(user, game: str) -> float:
    game = (game or "").lower()
    if game in ("multi", "", "valorant", "lol"):
        return 10**9

    appid = GAME_APPIDS.get(game)
    if not appid:
        return 10**9

    snap = (
        DailySnapshot.objects.filter(
            game_account__user=user,
            game_account__platform="steam",
            appid=appid,
        )
        .order_by("-date")
        .first()
    )
    if not snap:
        return 0.0
    return round((snap.playtime_forever or 0) / 60.0, 1)


def _check_join_allowed(clan, user):
    _assert_not_banned(clan, user)

    if ClanMembership.objects.filter(clan=clan, user=user).exists():
        raise ValueError("Ты уже состоишь в этом клане")

    if clan.max_members is not None:
        if clan.memberships.count() >= clan.max_members:
            raise ValueError("Клан заполнен")

    if clan.min_playtime_hours:
        hours = get_user_game_hours(user, clan.game)
        if hours < clan.min_playtime_hours:
            raise ValueError(
                f"Нужно минимум {clan.min_playtime_hours} ч. в игре клана "
                f"(у тебя ~{hours})"
            )


def get_clan_dashboard(clan):
    memberships = clan.memberships.select_related("user", "user__profile")
    stats = get_users_playtime([m.user_id for m in memberships])
    rows = []
    for m in memberships:
        st = stats.get(m.user_id) or {}
        two = int(st.get("two_weeks") or 0)
        total = int(st.get("total") or 0)
        rows.append({
            "user_id": m.user_id,
            "username": user_public_name(m.user),
            "role": m.role,
            "joined_at": m.joined_at,
            "two_weeks_playtime": two,
            "total_playtime": total,
            "is_inactive": two == 0,
        })
    rows.sort(key=lambda x: (-x["two_weeks_playtime"], -x["total_playtime"]))
    return rows


def _after_join(clan, user, membership):
    try:
        from apps.profiles.models import ClanActivity
        ClanActivity.objects.create(
            clan=clan,
            user=user,
            kind="joined",
            text=f"{user_public_name(user)} вступил в клан",
        )
    except Exception:
        pass
    try:
        from apps.users.services import notify
        if clan.owner_id != user.id:
            notify(
                clan.owner,
                kind="clan_join",
                title="Новый участник",
                body=f"{user_public_name(user)} вступил в {clan.name}",
                link="/clans",
            )
    except Exception:
        pass
    return membership


def join_clan_by_invite_code(user, invite_code: str) -> ClanMembership:
    code = (invite_code or "").strip().upper()
    try:
        clan = Clan.objects.get(invite_code=code)
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
    if not clan.is_open:
        raise ValueError("Клан закрытый — нужен инвайт-код")
    _check_join_allowed(clan, user)
    membership = ClanMembership.objects.create(clan=clan, user=user, role="member")
    return _after_join(clan, user, membership)