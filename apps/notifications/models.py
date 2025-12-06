from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from apps.core.models import TimeStampedModel

User = get_user_model()

class Notification(TimeStampedModel):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    verb = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    target = GenericForeignKey('content_type', 'object_id')
    
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Noti for {self.recipient.email}: {self.verb}"