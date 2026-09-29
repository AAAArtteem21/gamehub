MAX_LOGO_SIZE = 2 * 1024 * 1024
ALLOWED_LOGO_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

def clan_logo_url(clan, request=None):
    try:
        if not clan.logo:
            return None
        url = clan.logo.url  # /media/clans/...
        if request is not None:
            return request.build_absolute_uri(url)
        return url
    except (ValueError, AttributeError):
        return None