# apps/users/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import User

@shared_task
def check_expired_memberships():
    now = timezone.now()
    
    # Tìm những người có ngày hết hạn < hiện tại
    expired_users = User.objects.filter(membership_expires_at__lt=now)
    
    count = 0
    for user in expired_users:
        # Reset toàn bộ quyền lợi về mo
        user.job_posting_credits = 0 
        user.has_unlimited_posting = False
        user.can_view_contact = False
        user.membership_expires_at = None 
        
        user.save()
        count += 1
    
    return f"Đã quét xong: {count} tài khoản hết hạn đã bị reset."

# CRITICAL FIX #5: Async email cho UX tốt hơn (không block API đăng ký)
@shared_task
def send_welcome_email_task(user_id, user_email, user_full_name):
    """
    Gửi email chào mừng cho RECRUITER đăng ký (chạy background)
    Tách khỏi API để không làm chậm response time
    """
    from django.core.mail import send_mail
    from django.conf import settings
    from django.utils.translation import gettext as _
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        send_mail(
            subject=str(_('Account Registration - Pending Approval')),
            message=_(
                "Hello {name},\n\n"
                "Thank you for registering as a Recruiter on OneTop.\n\n"
                "Your account is currently pending approval by our admin team. "
                "You will receive another email once your account has been approved and you can start posting jobs.\n\n"
                "This process usually takes 1-2 business days.\n\n"
                "Best regards,\nOneTop Team"
            ).format(name=user_full_name),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,  # Raise exception để Celery retry
        )
        logger.info(f"Welcome email sent to user {user_id} ({user_email})")
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user_email}: {e}")
        raise  # Celery sẽ retry theo cấu hình