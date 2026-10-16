def user_public_name(user) -> str:
    if not user:
        return "?"
    profile = getattr(user, "profile", None)
    name = (getattr(profile, "display_name", None) or "").strip()
    if name:
        return name
    return (getattr(user, "username", None) or "?").strip() or "?"