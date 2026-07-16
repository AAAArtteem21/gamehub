from datetime import timedelta,date 
from django.utils import timezone
from django.db.models import Q,Sum
from django.db import models

from .models import ClanMembership,Clan
from apps.profiles.models import DailySnapshot

def get_clan_dashboard(clan: Clan):
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    memberships = list(
        ClanMembership.objects.filter(clan=clan).select_related("user")
    )
    user_ids = [m.user_id for m in memberships]

    from django.db.models import Case, When, IntegerField

    snapshots = (
        DailySnapshot.objects
        .filter(game_account__user_id__in=user_ids)
        .values("game_account__user_id")
        .annotate(
            today_total=Sum(Case(
                When(date=today, then="playtime_forever"),
                default=0, output_field=IntegerField()
            )),
            week_total=Sum(Case(
                When(date__gte=week_ago, then="playtime_forever"),
                default=0, output_field=IntegerField()
            )),
            month_total=Sum(Case(
                When(date__gte=month_ago, then="playtime_forever"),
                default=0, output_field=IntegerField()
            )),
        )
    )
    stats_by_user = {s["game_account__user_id"]: s for s in snapshots}

    last_active = (
        DailySnapshot.objects
        .filter(game_account__user_id__in=user_ids)
        .values("game_account__user_id")
        .annotate(last_date=models.Max("date"))
    )
    last_active_by_user = {s["game_account__user_id"]: s["last_date"] for s in last_active}

    result = []
    for membership in memberships:
        user = membership.user
        stats = stats_by_user.get(user.id, {})
        last_active_date = last_active_by_user.get(user.id)

        result.append({
            "user_id": user.id,
            "username": user.username,
            "role": membership.role,
            "joined_at": membership.joined_at,
            "today_playtime": stats.get("today_total", 0),
            "week_playtime": stats.get("week_total", 0),
            "month_playtime": stats.get("month_total", 0),
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

    return ClanMembership.objects.create(clan=clan, user=user, role="member")