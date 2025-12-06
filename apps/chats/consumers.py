# apps/chats/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from .tasks import save_and_broadcast_message # <--- Import task vừa tạo

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        # Chặn user chưa đăng nhập
        if self.user.is_anonymous:
            await self.close()
            return

        # Tham gia phòng chat
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Nhận tin nhắn từ Client -> Đẩy sang Celery -> Kết thúc
        """
        data = json.loads(text_data)
        message_text = data.get('message', '')
        
        if not message_text:
            return

        # --- THAY ĐỔI QUAN TRỌNG ---
        # Thay vì await self.save_message(...) (Chờ DB lưu xong mới chạy tiếp)
        # Ta gọi .delay() để ném sang Celery Worker xử lý.
        # Hàm này trả về ngay lập tức, giúp socket không bị nghẽn (Non-blocking).
        save_and_broadcast_message.delay(
            self.room_id, 
            str(self.user.id), # Chuyển UUID sang string để Celery serialize được
            message_text
        )

    async def chat_message(self, event):
        """
        Nhận tín hiệu từ Celery (qua Redis) và đẩy xuống Client
        """
        # Gửi message JSON về cho Client (Frontend)
        await self.send(text_data=json.dumps(event))