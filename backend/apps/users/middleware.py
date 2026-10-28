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


class RequestErrorLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code >= 400:
            user = getattr(request, "user", None)
            app_log(
                f"{request.method} {request.path} -> {response.status_code}",
                level="error" if response.status_code >= 500 else "warning",
                source="http",
                user=user if getattr(user, "pk", None) else None,
                path=request.path,
                method=request.method,
                status_code=response.status_code,
            )
        return response

