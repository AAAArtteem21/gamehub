from django.conf import settings

COOKIE_NAME = "gh_auth_token"


def set_auth_cookie(response, token_key: str):
    response.set_cookie(
        COOKIE_NAME,
        token_key,
        max_age=60 * 60 * 24 * 14,
        httponly=True,
        secure=True,
        samesite="None",
        path="/",
    )
    return response


def clear_auth_cookie(response):
    response.delete_cookie(COOKIE_NAME, path="/", samesite="None")
    return response