from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from apps.applications.models import Application
from apps.notifications.models import Notification

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