class SecurityHeadersMiddleware:
    """CSP, cache-control for API, extra security headers."""

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

        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://gamehub-gh6j.onrender.com "
            "https://api.steampowered.com https://steamcommunity.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none';"
        )
        response["Content-Security-Policy"] = csp

        path = request.path or ""
        if path.startswith("/api/"):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        return response