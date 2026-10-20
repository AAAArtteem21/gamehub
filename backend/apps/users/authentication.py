from rest_framework.authentication import TokenAuthentication


class CookieTokenAuthentication(TokenAuthentication):
    """
    Сначала Authorization: Token … (для отладки/скриптов),
    иначе cookie gh_auth_token (HttpOnly).
    """
    keyword = "Token"

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            return result

        raw = request.COOKIES.get("gh_auth_token")
        if not raw:
            return None
        return self.authenticate_credentials(raw.strip())