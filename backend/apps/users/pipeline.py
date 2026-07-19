from .models import UserProfile
from apps.profiles.integrations.steam_client import SteamClient
from apps.profiles.serivces import ProfileSyncService
from apps.profiles.models import GameAccount

from .models import UserProfile


def save_steam_profile(backend, user, response, *args, **kwargs):
    if backend.name != 'steam':
        return

    profile, _ = UserProfile.objects.get_or_create(user=user)
    player = response.get('player', {})

    steam_id = response.get('player', {}).get('steamid') or kwargs.get('uid')
    profile.steam_id = steam_id
    profile.avatar_url = player.get('avatarfull', profile.avatar_url)
    if not profile.display_name:
        profile.display_name = player.get('personaname', user.username)
    profile.save()
    game_account, created = GameAccount.objects.get_or_create(
        user=user, platform='steam', external_id=steam_id,
    )
    if created:
        try:
            ProfileSyncService(game_account).sync()
        except Exception:
            pass