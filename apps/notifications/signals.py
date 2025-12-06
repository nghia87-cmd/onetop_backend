from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _
from apps.applications.models import Application
from apps.notifications.models import Notification
from .tasks import send_websocket_notification  # Import Celery task

@receiver(post_save, sender=Application)
def create_application_notification(sender, instance, created, **kwargs):
    """
    Tạo notification khi có đơn ứng tuyển mới hoặc cập nhật trạng thái
    
    i18n: Sử dụng gettext() thay vì hardcoded strings
    """
    if created:
        job = instance.job
        recruiter = job.company.owner
        Notification.objects.create(
            recipient=recruiter,
            verb=_("submitted an application"),
            description=_("{candidate} has just applied for {job}").format(
                candidate=instance.candidate.full_name,
                job=job.title
            ),
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.id
        )
    else:
        if instance.status in ['INTERVIEW', 'REJECTED', 'ACCEPTED']:
            Notification.objects.create(
                recipient=instance.candidate,
                verb=_("updated application status"),
                description=_("Your application at {company} has been updated to: {status}").format(
                    company=instance.job.company.name,
                    status=instance.get_status_display()
                ),
                content_type=ContentType.objects.get_for_model(instance),
                object_id=instance.id
            )

@receiver(post_save, sender=Notification)
def broadcast_notification(sender, instance, created, **kwargs):
    """
    Gửi notification qua WebSocket (Async via Celery)
    
    Refactored: Sử dụng Celery task thay vì async_to_sync để:
    - Không block database transaction
    - Retry tự động nếu WebSocket server (Redis) bị lỗi
    - Giảm tải cho main Django process
    """
    if created:
        notification_data = {
            "id": str(instance.id),
            "verb": instance.verb,
            "description": instance.description,
            "is_read": False
        }
        
        # Gửi task async cho Celery worker
        send_websocket_notification.delay(
            recipient_id=instance.recipient.id,
            notification_data=notification_data
        )