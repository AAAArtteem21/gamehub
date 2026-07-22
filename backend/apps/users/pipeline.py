from .models import UserProfile
from apps.profiles.integrations.steam_client import SteamClient
from apps.profiles.serivces import ProfileSyncService
from apps.profiles.models import GameAccount

from .models import UserProfile


def save_steam_profile(backend, user, response, *args, **kwargs):
    if backend.name != "steam":
        return

    steam_id = kwargs.get("uid")
    if not steam_id:
        return

    player = SteamClient().get_player_summary(steam_id) or {}

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.steam_id = steam_id
    profile.avatar_url = player.get("avatarfull", profile.avatar_url)

    if not profile.display_name:
        profile.display_name = player.get("personaname", user.username)

    profile.save()

    game_account, created = GameAccount.objects.get_or_create(
        user=user,
        platform="steam",
        external_id=steam_id,
    )

    if created:
        try:
            ProfileSyncService(game_account).sync()
        except Exception:
            pass