import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

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
        data = json.loads(text_data)
        message_text = data.get('message', '')
        
        if not message_text:
            return

        new_msg = await self.save_message(self.room_id, self.user, message_text)

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
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_message(self, conversation_id, user, text):
        from .models import Conversation, Message
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            msg = Message.objects.create(
                conversation=conversation,
                sender=user,
                text=text
            )
            conversation.save() 
            return msg
        except Conversation.DoesNotExist:
            return None