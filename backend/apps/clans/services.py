from django.db.models import OuterRef, Subquery

from apps.profiles.models import DailySnapshot
from .models import Clan, ClanMembership


def get_users_playtime(user_ids):
    """
    {user_id: {"two_weeks": минуты, "total": минуты}}
    Берём последний снапшот каждой игры у Steam-аккаунтов пользователей.
    """
    user_ids = list(user_ids)
    if not user_ids:
        return {}

    newest_date = (
        DailySnapshot.objects
        .filter(game_account=OuterRef("game_account"), appid=OuterRef("appid"))
        .order_by("-date")
        .values("date")[:1]
    )
    rows = (
        DailySnapshot.objects
        .filter(
            game_account__user_id__in=user_ids,
            game_account__platform="steam",
            date=Subquery(newest_date),
        )
        .values_list("game_account__user_id", "appid", "playtime_forever", "playtime_2weeks")
    )

    # (user, appid) -> максимум, чтобы дубли Steam-аккаунтов не задвоили часы
    best = {}
    for uid, appid, forever, two_weeks in rows:
        cur = best.get((uid, appid))
        forever = forever or 0
        two_weeks = two_weeks or 0
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


def join_clan_by_invite_code(user, invite_code: str) -> ClanMembership:
    try:
        clan = Clan.objects.get(invite_code=invite_code)
    except Clan.DoesNotExist:
        raise ValueError("Неверный код приглашения")

    if ClanMembership.objects.filter(clan=clan, user=user).exists():
        raise ValueError("Ты уже состоишь в этом клане")

    membership = ClanMembership.objects.create(clan=clan, user=user, role="member")

    try:
        from apps.profiles.models import ClanActivity
        ClanActivity.objects.create(
            clan=clan, user=user, kind="joined",
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