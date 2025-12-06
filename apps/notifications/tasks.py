"""
Celery Tasks cho Notifications
Tách việc gửi WebSocket notification ra khỏi database transaction
"""
from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_websocket_notification(self, recipient_id, notification_data):
    """
    Gửi notification qua WebSocket
    
    Args:
        recipient_id: ID của user nhận notification
        notification_data: dict chứa {id, verb, description, is_read}
    """
    try:
        channel_layer = get_channel_layer()
        group_name = f"user_{recipient_id}"
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "send_notification",
                "data": notification_data
            }
        )
        
        logger.info(f"Sent WebSocket notification to user {recipient_id}")
        
    except Exception as exc:
        logger.error(f"Failed to send WebSocket notification: {exc}")
        # Retry sau 5 giây nếu thất bại
        raise self.retry(exc=exc, countdown=5)
