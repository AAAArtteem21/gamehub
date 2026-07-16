from .models import UserProfile


def save_steam_profile(bakcend,user,response,*args,**kwargs):
    if bakcend.name != 'steam':
        return 

    profile, _ = UserProfile.objects.get_or_create(user=user)
    player = response.get('player',{})

    profile.steam_id = response.get('player',{}).get('steamid') or kwargs.get('uid')
    profile.avatar_url = player.get('avatarfull',profile.avatar_url)
    if not profile.display_name:
        profile.display_name = player.get('personaname',user.username)
    profile.save()