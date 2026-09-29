from .models import Notification


def notify(user, *, kind, title, body="", link=""):
    if not user:
        return None
    return Notification.objects.create(
        user=user,
        kind=kind,
        title=str(title)[:120],
        body=str(body or "")[:280],
        link=str(link or "")[:255],
    )