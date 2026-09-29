from .models import UserProfile
from .services import notify

XP_PER_LEVEL = 100

XP_SYNC = 10
XP_LFG_POST = 15
XP_LFG_RESPONSE = 10
XP_CLAN_JOIN = 10
XP_REFERRAL_INVITER = 50
XP_REFERRAL_INVITEE = 30


def _level_from_xp(xp: int) -> int:
    return max(1, (xp or 0) // XP_PER_LEVEL + 1)


def get_or_create_profile(user) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def add_xp(user, amount: int, *, reason: str = ""):
    if not user or amount <= 0:
        return None
    profile = get_or_create_profile(user)
    old_level = profile.level or 1
    profile.xp = (profile.xp or 0) + amount
    profile.level = _level_from_xp(profile.xp)
    profile.save(update_fields=["xp", "level", "updated_at"])

    if profile.level > old_level:
        try:
            notify(
                user,
                kind="level_up",
                title=f"Уровень {profile.level}!",
                body=f"+{amount} XP · {reason}" if reason else f"Теперь GH {profile.level}",
                link="/profile",
            )
        except Exception:
            pass
        if profile.level >= 6 and profile.level % 2 == 0:
            profile.boost_credits = (profile.boost_credits or 0) + 1
            profile.save(update_fields=["boost_credits"])

    return profile


def progress_payload(profile: UserProfile) -> dict:
    xp = profile.xp or 0
    level = profile.level or 1
    into = xp % XP_PER_LEVEL
    return {
        "xp": xp,
        "level": level,
        "xp_into_level": into,
        "xp_per_level": XP_PER_LEVEL,
        "pct": min(100, round(into / XP_PER_LEVEL * 100)) if XP_PER_LEVEL else 0,
        "boost_credits": profile.boost_credits or 0,
        "tags": profile.tags or [],
        "referral_code": profile.referral_code or "",
        "referral_link": f"?ref={profile.referral_code}" if profile.referral_code else "",
        "has_referrer": bool(profile.referred_by_id),
    }