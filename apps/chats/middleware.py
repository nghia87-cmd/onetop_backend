import jwt
from urllib.parse import parse_qs
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware

User = get_user_model()

@database_sync_to_async
def get_user(token_key):
    try:
        payload = jwt.decode(token_key, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get('user_id')
        if user_id:
            return User.objects.get(id=user_id)
        return AnonymousUser()
    except (jwt.ExpiredSignatureError, jwt.DecodeError, User.DoesNotExist):
        return AnonymousUser()

class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        if token:
            scope["user"] = await get_user(token)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)