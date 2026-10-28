from .logging_utils import app_log

class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        response["X-Content-Type-Options"] = "nosniff"
        response["Referrer-Policy"] = "same-origin"
        response["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )
        response.headers.setdefault("X-Frame-Options", "DENY")

        path = (request.path or "").lower()


        if (
            path.startswith("/auth/")
            or "login/steam" in path
            or path.rstrip("/").endswith("/steam")
            or "/steam/" in path
        ):
            return response

        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://gameeyes.onrender.com "
            "https://api.steampowered.com https://steamcommunity.com; "
            "form-action 'self' https://steamcommunity.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "object-src 'none';"
        )

        if path.startswith("/api/"):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        return response


SKIP_PREFIXES = ("/static/", "/media/", "/health")


class RequestErrorLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        path = request.path or ""
        if any(path.startswith(p) for p in SKIP_PREFIXES):
            return response

        code = response.status_code

        if code >= 400:
            app_log(
                f"{request.method} {path} → {code}",
                level="error" if code >= 500 else "warning",
                source="http",
                request=request,
                status_code=code,
            )
            return response

        if code < 400 and request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if path.startswith("/api/"):
                app_log(
                    f"{request.method} {path} → {code}",
                    level="info",
                    source="api",
                    request=request,
                    status_code=code,
                )

        return response

