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

        path = request.path or ""

        if path.startswith("/auth/"):
            response["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "form-action 'self' https://steamcommunity.com; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "object-src 'none';"
            )
            return response

        response["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://gameeyes.onrender.com "
            "https://api.steampowered.com https://steamcommunity.com; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "object-src 'none';"
        )

        if path.startswith("/api/"):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        return response