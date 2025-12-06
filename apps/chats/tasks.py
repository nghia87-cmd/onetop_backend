# apps/chats/tasks.py
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()

@shared_task
def save_and_broadcast_message(conversation_id, user_id, message_text):
    """
    Task chạy ngầm (Background):
    1. Lưu tin nhắn vào Postgres
    2. Gửi tin nhắn đó đến Group Chat (Redis Channel)
    """
    try:
        # 1. Lưu tin nhắn vào Database
        user = User.objects.get(id=user_id)
        conversation = Conversation.objects.get(id=conversation_id)
        
        new_msg = Message.objects.create(
            conversation=conversation,
            sender=user,
            text=message_text
        )
        
        # Cập nhật thời gian nhắn tin cuối cùng (để sắp xếp list chat)
        conversation.save()

        # 2. Broadcast tin nhắn tới Group (Redis)
        # Vì Celery chạy đồng bộ (Sync), ta cần async_to_sync để gọi channel layer
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{conversation_id}', # Tên nhóm (Room Group Name)
            {
                'type': 'chat_message',
                'id': str(new_msg.id),
                'message': new_msg.text,
                'sender_email': user.email,
                'sender_id': str(user.id),
                'created_at': new_msg.created_at.isoformat()
            }
        )
        return f"Message {new_msg.id} saved & broadcasted."
    
    except Exception as e:
        return f"Error saving message: {str(e)}"