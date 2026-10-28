from django.contrib.auth import get_user_model

def app_log(
    message: str,
    *,
    level: str = "info",
    source: str = "",
    user=None,
    path: str = "",
    method: str = "",
    status_code = None,
    extra = None,
):
    from .models import AppLog

    try:
        AppLog.objects.create(
            level=level,
            source=source[:64],
            message=str(message)[:4000],
            path=(path or "")[:255],
            method=(method or "")[:10],
            status_code=status_code,
            user=user if getattr(user, "is_authenticated", False) else None,
            extra=extra or {},
        )
    except Exception:
        pass
