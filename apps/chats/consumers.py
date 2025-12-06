import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()

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
        # Kiểm tra xem group_name đã được khởi tạo chưa để tránh lỗi
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Nhận tin nhắn từ Client -> Lưu DB (Async) -> Broadcast ngay lập tức
        """
        data = json.loads(text_data)
        message_text = data.get('message', '')
        
        if not message_text:
            return

        # 1. Lưu tin nhắn vào Database (Sử dụng hàm trợ giúp bất đồng bộ)
        try:
            new_msg = await self.save_message(self.room_id, self.user.id, message_text)
        except Exception as e:
            # Gửi lỗi về cho client nếu cần (hoặc log lại)
            await self.send(text_data=json.dumps({'error': 'Failed to save message'}))
            return

        # 2. Broadcast tin nhắn tới Group (Redis) ngay lập tức
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'id': str(new_msg.id),
                'message': new_msg.text,
                'sender_email': self.user.email,
                'sender_id': str(self.user.id),
                'created_at': new_msg.created_at.isoformat()
            }
        )

    async def chat_message(self, event):
        """
        Nhận tín hiệu từ Group (Redis) và đẩy xuống Client
        """
        # Gửi message JSON về cho Client (Frontend)
        # Loại bỏ trường 'type' không cần thiết khi gửi xuống client
        event_data = event.copy()
        if 'type' in event_data:
            del event_data['type']
            
        await self.send(text_data=json.dumps(event_data))

    @database_sync_to_async
    def save_message(self, conversation_id, user_id, message_text):
        """
        Hàm đồng bộ để tương tác với Database, được wrap để chạy trong async context
        """
        user = User.objects.get(id=user_id)
        conversation = Conversation.objects.get(id=conversation_id)
        
        new_msg = Message.objects.create(
            conversation=conversation,
            sender=user,
            text=message_text
        )
        
        # Cập nhật thời gian nhắn tin cuối cùng cho cuộc trò chuyện
        conversation.save() # Auto update updated_at/last_message_at
        
        return new_msg