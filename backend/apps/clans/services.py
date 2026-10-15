from datetime import datetime

from django.utils import timezone as dj_timezone

from apps.profiles.models import DailySnapshot
from django.db.models import OuterRef, Subquery

from .models import Clan, ClanMembership


def get_users_playtime(user_ids):
    user_ids = list(user_ids)
    if not user_ids:
        return {}

    newest_date = (
        DailySnapshot.objects.filter(
            game_account=OuterRef("game_account"), appid=OuterRef("appid")
        )
        .order_by("-date")
        .values("date")[:1]
    )
    rows = (
        DailySnapshot.objects.filter(
            game_account__user_id__in=user_ids,
            game_account__platform="steam",
            date=Subquery(newest_date),
        ).values_list("game_account__user_id", "appid", "playtime_forever", "playtime_2weeks")
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
    memberships = list(ClanMembership.objects.filter(clan=clan).select_related("user"))
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


def _check_join_allowed(clan: Clan, user) -> None:
    if ClanMembership.objects.filter(clan=clan, user=user).exists():
        raise ValueError("Ты уже состоишь в этом клане")

    count = clan.memberships.count()
    if clan.max_members is not None and count >= clan.max_members:
        raise ValueError("Клан заполнен")

    if clan.join_hours_start is not None and clan.join_hours_end is not None:
        hour = dj_timezone.localtime(dj_timezone.now()).hour
        start, end = int(clan.join_hours_start), int(clan.join_hours_end)
        if start <= end:
            ok = start <= hour < end
        else:
            # через полночь, напр. 22–6
            ok = hour >= start or hour < end
        if not ok:
            raise ValueError(
                f"Сейчас нельзя вступить (окно входа {start:02d}:00–{end:02d}:00)"
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

    if not clan.is_open:
        raise ValueError("Клан закрытый — нужен код приглашения")

    _check_join_allowed(clan, user)
    membership = ClanMembership.objects.create(clan=clan, user=user, role="member")
    return _after_join(clan, user, membership)