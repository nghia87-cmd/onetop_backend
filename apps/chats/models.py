from django.db import models
from django.core.validators import FileExtensionValidator
from apps.core.models import TimeStampedModel
from apps.core.validators import validate_file_size
from django.contrib.auth import get_user_model
from apps.jobs.models import Job

User = get_user_model()

class Conversation(TimeStampedModel):
    participant1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_p1')
    participant2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations_as_p2')
    
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True)
    last_message_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('participant1', 'participant2', 'job')
        ordering = ['-last_message_at']

    def __str__(self):
        return f"Chat: {self.participant1.email} & {self.participant2.email}"

class Message(TimeStampedModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    
    text = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to='chat_attachments/', 
        null=True, 
        blank=True,
        validators=[
            validate_file_size,  # Max 5MB
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'zip']
            )
        ],
        help_text='Allowed: PDF, DOC, DOCX, JPG, PNG, GIF, ZIP. Max size: 5MB'
    )
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Msg from {self.sender.email}"