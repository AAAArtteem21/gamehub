from django.contrib.auth.signals import user_login_failed, user_logged_in
from django.dispatch import receiver
from .logging_utils import app_log

@receiver(user_login_failed)
def on_login_failed(sender, credintials, request, **kwargs):
    username= (credintials or {}).get("username", "")
    app_log(
        f"Неудачный вход {username!r}",
        level="warning",
        source="admin_auth",
        request=request,
        status_code=401,
        extra={"username": username},
    )

@receiver(user_logged_in)
def on_login_ok(sender, request, user, **kwargs):
    app_log(
        f"Вход: {user.username}",
        level="info",
        source="admin_auth",
        request=request,
        user=user,
        status_code=200,
    )
