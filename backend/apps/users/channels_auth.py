from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import AnonymousUser


@database_sync_to_async
def get_user_from_token(token_key):
    try:
        token = Token.objects.select_related('user').get(key=token_key)
        return token.user
    except Token.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        params = dict(
            pair.split('=', 1) for pair in query_string.split('&') if '=' in pair
        )
        token_key = params.get('token')
        scope['user'] = await get_user_from_token(token_key) if token_key else AnonymousUser()
        return await super().__call__(scope, receive, send)