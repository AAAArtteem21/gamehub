from datetime import timedelta,date 
from django.utils import timezone
from django.db.models import Q,Sum
from django.db import models
from django.utils import timezone as dj_timezone
from collections import defaultdict

from .models import ClanMembership,Clan
from apps.profiles.models import DailySnapshot


# apps/clans/services.py
from collections import defaultdict
from datetime import timedelta
from django.utils import timezone as dj_timezone
from .models import Clan, ClanMembership
from apps.profiles.models import DailySnapshot


def _period_activity(user_ids, start_date, end_date):
    """
    Минуты, наигранные в [start_date, end_date] по дельте playtime_forever.
    user_ids: iterable of user id
    """
    from collections import defaultdict
    from apps.profiles.models import DailySnapshot

    if not user_ids:
        return {}

    snapshots = (
        DailySnapshot.objects
        .filter(game_account__user_id__in=user_ids, date__lte=end_date)
        .select_related("game_account")
        .order_by("date")
    )

    # (user_id, appid) -> list[(date, playtime_forever)]
    series = defaultdict(list)
    for s in snapshots:
        series[(s.game_account.user_id, s.appid)].append(
            (s.date, int(s.playtime_forever or 0))
        )

    result = defaultdict(int)

    for (user_id, appid), pts in series.items():
        if not pts:
            continue

        # последний снимок в периоде (date <= end_date, date >= start_date предпочтительно)
        in_period = [(d, v) for d, v in pts if start_date <= d <= end_date]
        before = [(d, v) for d, v in pts if d < start_date]

        if not in_period:
            continue

        latest_val = in_period[-1][1]

        if before:
            base_val = before[-1][1]  # последний снимок ДО периода
        else:
            # нет истории до периода → берём первый снимок внутри периода
            # дельта только если есть 2+ точки внутри периода
            if len(in_period) >= 2:
                base_val = in_period[0][1]
            else:
                # один снимок и нет baseline — НЕ считаем весь forever за "сегодня/неделю"
                continue

        delta = latest_val - base_val
        if delta > 0:
            result[user_id] += delta

    return dict(result)

def get_clan_dashboard(clan: Clan):
    today = dj_timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    memberships = list(ClanMembership.objects.filter(clan=clan).select_related("user"))
    user_ids = [m.user_id for m in memberships]

    today_activity = _period_activity(user_ids, today, today)
    week_activity = _period_activity(user_ids, week_ago, today)
    month_activity = _period_activity(user_ids, month_ago, today)

    last_active_by_user = {}
    for s in DailySnapshot.objects.filter(game_account__user_id__in=user_ids).select_related('game_account'):
        uid = s.game_account.user_id
        if uid not in last_active_by_user or s.date > last_active_by_user[uid]:
            last_active_by_user[uid] = s.date

    result = []
    for membership in memberships:
        user = membership.user
        last_active_date = last_active_by_user.get(user.id)
        result.append({
            "user_id": user.id,
            "username": user.username,
            "role": membership.role,
            "joined_at": membership.joined_at,
            "today_playtime": today_activity.get(user.id, 0),
            "week_playtime": week_activity.get(user.id, 0),
            "month_playtime": month_activity.get(user.id, 0),
            "last_active_date": last_active_date,
            "is_inactive": last_active_date is None or last_active_date < week_ago,
        })

    result.sort(key=lambda x: (x["last_active_date"] is None,
                                 -(x["last_active_date"].toordinal() if x["last_active_date"] else 0)))
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