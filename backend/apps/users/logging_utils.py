def _client_ip(request):
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def app_log(
    message,
    *,
    level="info",
    source="",
    user=None,
    request=None,
    path="",
    method="",
    status_code=None,
    extra=None,
):
    from .models import AppLog

    try:
        if request is not None:
            path = path or getattr(request, "path", "") or ""
            method = method or getattr(request, "method", "") or ""
            if user is None:
                u = getattr(request, "user", None)
                if getattr(u, "is_authenticated", False):
                    user = u
            ip = _client_ip(request)
        else:
            ip = None

        AppLog.objects.create(
            level=level,
            source=(source or "")[:64],
            message=str(message)[:4000],
            path=(path or "")[:255],
            method=(method or "")[:10],
            status_code=status_code,
            ip=ip,
            user=user if getattr(user, "pk", None) else None,
            extra=extra or {},
        )
    except Exception:
        pass