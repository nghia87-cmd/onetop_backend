"""
WebSocket Ticket Service
Tạo one-time ticket cho WebSocket authentication
Ticket có thời gian sống ngắn để tránh lộ token
"""
import secrets
import time
from django.core.cache import cache
from django.conf import settings


class WebSocketTicketService:
    """Service quản lý one-time tickets cho WebSocket"""
    
    TICKET_PREFIX = 'ws_ticket:'
    TICKET_EXPIRY = settings.WEBSOCKET_TICKET_EXPIRY  # Lấy từ settings thay vì hardcode
    
    @classmethod
    def generate_ticket(cls, user_id: int) -> str:
        """
        Tạo ticket ngẫu nhiên cho user
        
        Args:
            user_id: ID của user
            
        Returns:
            ticket: Random string (32 chars)
        """
        ticket = secrets.token_urlsafe(32)
        cache_key = f"{cls.TICKET_PREFIX}{ticket}"
        
        # Store user_id trong cache với TTL = 10s
        cache.set(cache_key, user_id, cls.TICKET_EXPIRY)
        
        return ticket
    
    @classmethod
    def verify_ticket(cls, ticket: str) -> int:
        """
        Verify ticket và trả về user_id
        Ticket chỉ dùng được 1 lần (delete after use)
        
        Args:
            ticket: Ticket string
            
        Returns:
            user_id: ID của user, hoặc None nếu ticket không hợp lệ
        """
        if not ticket:
            return None
            
        cache_key = f"{cls.TICKET_PREFIX}{ticket}"
        user_id = cache.get(cache_key)
        
        if user_id:
            # Delete ticket ngay sau khi verify (one-time use)
            cache.delete(cache_key)
            
        return user_id
