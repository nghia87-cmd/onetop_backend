import os
from django.core.asgi import get_asgi_application

# Thiết lập môi trường trước khi import channels
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onetop_backend.settings')
# Khởi tạo Django HTTP application trước
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from apps.chats.middleware import JwtAuthMiddlewareStack # Middleware xác thực JWT bạn đã có
import apps.chats.routing
import apps.notifications.routing # Import routing vừa tạo

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JwtAuthMiddlewareStack(
        URLRouter(
            # Gộp routing của Chat và Notification lại
            apps.chats.routing.websocket_urlpatterns +
            apps.notifications.routing.websocket_urlpatterns
        )
    ),
})