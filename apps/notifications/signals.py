from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from apps.applications.models import Application
from apps.notifications.models import Notification
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver(post_save, sender=Application)
def create_application_notification(sender, instance, created, **kwargs):
    if created:
        job = instance.job
        recruiter = job.company.owner
        Notification.objects.create(
            recipient=recruiter,
            verb="đã nộp đơn ứng tuyển",
            description=f"{instance.candidate.full_name} vừa nộp đơn vào vị trí {job.title}",
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.id
        )
    else:
        if instance.status in ['INTERVIEW', 'REJECTED', 'ACCEPTED']:
            Notification.objects.create(
                recipient=instance.candidate,
                verb="đã cập nhật trạng thái hồ sơ",
                description=f"Hồ sơ của bạn tại {instance.job.company.name} đã chuyển sang: {instance.get_status_display()}",
                content_type=ContentType.objects.get_for_model(instance),
                object_id=instance.id
            )

@receiver(post_save, sender=Notification)
def broadcast_notification(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        group_name = f"user_{instance.recipient.id}"
        
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "send_notification",
                "data": {
                    "id": str(instance.id),
                    "verb": instance.verb,
                    "description": instance.description,
                    "is_read": False
                }
            }
        )