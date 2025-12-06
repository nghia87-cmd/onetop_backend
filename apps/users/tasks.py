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