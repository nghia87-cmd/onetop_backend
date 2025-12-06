"""
Optimistic Locking Helper
Giải pháp thay thế Pessimistic Locking (select_for_update) cho high-concurrency scenarios

WHEN TO USE:
- Traffic > 10,000 concurrent users
- Deadlock xảy ra thường xuyên với select_for_update()
- Read operations nhiều hơn Write operations (90% read, 10% write)

HOW IT WORKS:
- Mỗi model có thêm field 'version' (IntegerField)
- Mỗi lần update, version += 1
- Nếu version đã thay đổi (có người khác update trước), retry

ADVANTAGES:
- Không lock database rows → Better scalability
- Không có Deadlock risk
- Phù hợp với distributed systems

DISADVANTAGES:
- Phải retry khi conflict (acceptable với retry_on_conflict decorator)
- Cần thêm field 'version' vào model
"""

from django.db import transaction
from django.db.models import F
from functools import wraps
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def retry_on_conflict(max_retries=None):
    """
    Decorator tự động retry khi gặp OptimisticLockError
    
    Usage:
        @retry_on_conflict(max_retries=3)
        def update_user_credits(user_id, amount):
            user = User.objects.get(id=user_id)
            # ... business logic
            user.save_with_version_check()
    
    Args:
        max_retries: Số lần retry tối đa (default lấy từ settings)
    """
    if max_retries is None:
        max_retries = getattr(settings, 'OPTIMISTIC_LOCK_MAX_RETRIES', 3)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except OptimisticLockError as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Optimistic lock conflict in {func.__name__}, "
                            f"retry {attempt + 1}/{max_retries}"
                        )
                        continue
                    else:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded in {func.__name__}"
                        )
                        raise
            
            raise last_exception
        
        return wrapper
    return decorator


class OptimisticLockError(Exception):
    """Raised when optimistic lock version mismatch"""
    pass


class OptimisticLockMixin:
    """
    Mixin để thêm Optimistic Locking cho Django Models
    
    Usage:
        from django.db import models
        from apps.payments.optimistic_locking import OptimisticLockMixin
        
        class User(OptimisticLockMixin, models.Model):
            username = models.CharField(max_length=150)
            job_posting_credits = models.IntegerField(default=0)
            version = models.IntegerField(default=0)  # REQUIRED
            
            class Meta:
                db_table = 'users_user'
        
        # Usage
        user = User.objects.get(id=1)
        user.job_posting_credits += 10
        user.save_with_version_check()  # Raises OptimisticLockError if conflict
    """
    
    def save_with_version_check(self, *args, **kwargs):
        """
        Save với version check để phát hiện concurrent modifications
        
        Raises:
            OptimisticLockError: Nếu version đã thay đổi (có người khác update trước)
        """
        if not hasattr(self, 'version'):
            raise AttributeError(
                f"{self.__class__.__name__} must have 'version' field "
                "to use OptimisticLockMixin"
            )
        
        # Lưu version hiện tại
        current_version = self.version
        
        # Tăng version cho lần update này
        self.version = F('version') + 1
        
        # Force update (không tạo mới)
        kwargs['force_update'] = True
        
        # Chỉ update nếu version = current_version
        with transaction.atomic():
            updated_rows = self.__class__.objects.filter(
                pk=self.pk,
                version=current_version
            ).update(
                version=F('version') + 1,
                **{
                    field.name: getattr(self, field.name)
                    for field in self._meta.fields
                    if field.name not in ['id', 'version'] and not field.primary_key
                }
            )
            
            if updated_rows == 0:
                # Version đã thay đổi → có conflict
                logger.warning(
                    f"Optimistic lock conflict for {self.__class__.__name__} "
                    f"pk={self.pk}, expected version={current_version}"
                )
                raise OptimisticLockError(
                    f"Record was modified by another transaction. "
                    f"Expected version {current_version}, "
                    f"but record has been updated."
                )
            
            # Refresh instance để có version mới
            self.refresh_from_db()


# Example: Payment Service với Optimistic Locking
class OptimisticPaymentService:
    """
    Alternative PaymentService using Optimistic Locking
    
    Dùng khi:
    - Traffic cao (> 10k concurrent)
    - Gặp Deadlock với select_for_update()
    - System distributed (multiple app servers)
    """
    
    @staticmethod
    @retry_on_conflict(max_retries=3)
    def activate_membership_optimistic(user, package):
        """
        Kích hoạt membership với Optimistic Locking
        
        So với Pessimistic Locking (select_for_update):
        - ✅ No database row locks
        - ✅ No deadlock risk
        - ✅ Better scalability
        - ⚠️ Cần retry khi conflict (acceptable)
        """
        from django.utils import timezone
        from datetime import timedelta
        from apps.users.models import User
        
        # Không lock row, chỉ đọc data
        user = User.objects.get(pk=user.pk)
        
        now = timezone.now()
        
        # Business logic
        if user.membership_expires_at and user.membership_expires_at > now:
            user.membership_expires_at += timedelta(days=package.duration_days)
        else:
            user.membership_expires_at = now + timedelta(days=package.duration_days)
        
        if package.package_type == 'SUBSCRIPTION':
            if package.allow_unlimited_posting:
                user.has_unlimited_posting = True
            if package.allow_view_contact:
                user.can_view_contact = True
        else:
            # Credit package
            user.job_posting_credits = F('job_posting_credits') + package.job_posting_limit
        
        # Save với version check
        # Nếu có conflict, OptimisticLockError sẽ được raise
        # và decorator retry_on_conflict sẽ tự động retry
        user.save_with_version_check()
        
        logger.info(
            f"Membership activated for user {user.id} using Optimistic Locking"
        )
        
        return user


# Migration helper để thêm version field
def get_migration_code():
    """
    Code mẫu để thêm vào migration file:
    
    operations = [
        migrations.AddField(
            model_name='user',
            name='version',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='transaction',
            name='version',
            field=models.IntegerField(default=0),
        ),
    ]
    """
    return """
# Migration example for Optimistic Locking
# File: apps/users/migrations/000X_add_version_field.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_add_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='version',
            field=models.IntegerField(default=0, help_text='Optimistic locking version'),
        ),
    ]
"""
