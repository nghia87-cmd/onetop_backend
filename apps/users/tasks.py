# apps/users/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import User

@shared_task
def check_expired_memberships():
    """
    Task chạy định kỳ mỗi ngày để kiểm tra các User hết hạn gói VIP.
    Nếu hết hạn -> Reset số lượt đăng tin về 0 và xóa ngày hết hạn.
    """
    now = timezone.now()
    
    # Tìm những người có ngày hết hạn < hiện tại
    expired_users = User.objects.filter(membership_expires_at__lt=now)
    
    count = 0
    for user in expired_users:
        # Logic hạ cấp: Reset quyền lợi
        user.job_posting_credits = 0 
        user.membership_expires_at = None # Xóa ngày hết hạn để không quét lại nữa
        user.save()
        count += 1
    
    return f"Đã quét xong: {count} tài khoản hết hạn đã bị reset."