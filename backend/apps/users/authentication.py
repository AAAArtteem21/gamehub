from rest_framework.authentication import TokenAuthentication


class CookieTokenAuthentication(TokenAuthentication):
    """
    1) Authorization: Token <key>
    2) cookie gh_auth_token
    """

    def authenticate(self, request):
        header_auth = super().authenticate(request)
        if header_auth is not None:
            return header_auth

        raw = request.COOKIES.get("gh_auth_token")
        if not raw:
            return None
        return self.authenticate_credentials(raw)