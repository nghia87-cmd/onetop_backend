# Signal to send email when RECRUITER account is approved
# Add this to apps/users/signals.py (create if doesn't exist)

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import datetime

User = get_user_model()


@receiver(post_save, sender=User)
def notify_recruiter_approval(sender, instance, created, **kwargs):
    """
    Send email notification when RECRUITER account status changes from inactive to active
    
    Usage: Admin approves recruiter by setting is_active=True in Django Admin
    """
    # Only process for RECRUITER accounts that are being activated (not newly created)
    if not created and instance.user_type == 'RECRUITER' and instance.is_active:
        # Check if this was a status change (was inactive, now active)
        # We check update_fields to see if is_active was modified
        update_fields = kwargs.get('update_fields')
        
        # If update_fields is None, it means save() was called without specific fields
        # In this case, we should check if the user was previously inactive
        if update_fields is None or 'is_active' in update_fields:
            try:
                # Render email template
                context = {
                    'user': instance,
                    'SITE_URL': getattr(settings, 'FRONTEND_URL', 'http://localhost:3000'),
                    'current_year': datetime.now().year
                }
                
                html_content = render_to_string('emails/recruiter_approved.html', context)
                text_content = strip_tags(html_content)
                
                send_mail(
                    subject='Your OneTop Recruiter Account Has Been Approved!',
                    message=text_content,
                    html_message=html_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.email],
                    fail_silently=True,
                )
                
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Sent approval email to recruiter {instance.email}")
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send approval email to {instance.email}: {e}")
