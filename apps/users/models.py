from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.payments.optimistic_locking import OptimisticLockMixin
import uuid

class User(OptimisticLockMixin, AbstractUser, TimeStampedModel):
    class UserType(models.TextChoices):
        CANDIDATE = 'CANDIDATE', _('Ứng viên')
        RECRUITER = 'RECRUITER', _('Nhà tuyển dụng')
        ADMIN = 'ADMIN', _('Quản trị viên')

    pkid = models.BigAutoField(primary_key=True, editable=False)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    email = models.EmailField(_('Email Address'), unique=True)
    full_name = models.CharField(_('Full Name'), max_length=255)
    phone_number = models.CharField(_('Phone Number'), max_length=15, blank=True, default='', help_text="Số điện thoại liên hệ")
    avatar = models.ImageField(upload_to='avatars/', default='default_avatar.png', null=True, blank=True)
    
    # 2 trường quan trọng cho gói dịch vụ (Payments)
    job_posting_credits = models.IntegerField(
        default=0, 
        help_text="Số lượt đăng tin còn lại",
        db_index=True  # INDEX: Hay query khi check credits
    )
    membership_expires_at = models.DateTimeField(
        null=True, 
        blank=True, 
        help_text="Ngày hết hạn gói dịch vụ",
        db_index=True  # INDEX: Hay query khi check expired
    )

    has_unlimited_posting = models.BooleanField(default=False, help_text="Được phép đăng tin không giới hạn")
    can_view_contact = models.BooleanField(default=False, help_text="Được phép xem thông tin liên hệ ứng viên")

    user_type = models.CharField(
        max_length=20, 
        choices=UserType.choices, 
        default=UserType.CANDIDATE
    )
    
    # CRITICAL FIX: Add version field for Optimistic Locking (prevents race conditions)
    # This enables concurrent payment processing without database deadlocks
    version = models.IntegerField(
        default=0,
        help_text="Version field for optimistic locking - auto-incremented on each update"
    )

    USERNAME_FIELD = 'email' # Đăng nhập bằng Email
    REQUIRED_FIELDS = ['username', 'full_name']

    def __str__(self):
        return self.email