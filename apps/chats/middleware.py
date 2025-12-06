"""
WebSocket Authentication Middleware
Sử dụng one-time ticket thay vì JWT token để bảo mật hơn
"""
from urllib.parse import parse_qs
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from apps.core.websocket_ticket import WebSocketTicketService

User = get_user_model()


@database_sync_to_async
def get_user_by_ticket(ticket):
    """
    Verify ticket và load user
    Ticket chỉ dùng được 1 lần (one-time use)
    """
    try:
        user_id = WebSocketTicketService.verify_ticket(ticket)
        if user_id:
            return User.objects.get(id=user_id)
        return AnonymousUser()
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    """
    WebSocket Auth Middleware using one-time ticket
    
    Flow:
    1. Client POST /api/v1/ws-ticket/ -> get ticket
    2. Client connect ws://.../?ticket=<ticket>
    3. Middleware verify ticket (expires in 10s, one-time use)
    """
    
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        ticket = query_params.get("ticket", [None])[0]

        if ticket:
            scope["user"] = await get_user_by_ticket(ticket)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)