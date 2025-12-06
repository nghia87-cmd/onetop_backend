"""
Soft Delete Mixin & Manager
Enterprise pattern cho việc xóa dữ liệu an toàn

WHY SOFT DELETE?
- ✅ Data recovery: Khôi phục nếu xóa nhầm
- ✅ Audit trail: Biết ai xóa, khi nào xóa
- ✅ Compliance: Tuân thủ quy định lưu trữ dữ liệu
- ✅ Analytics: Phân tích dữ liệu đã xóa (churn rate, etc.)

USAGE:
    from apps.core.models import SoftDeleteMixin, SoftDeleteManager
    
    class Job(SoftDeleteMixin, models.Model):
        title = models.CharField(max_length=255)
        objects = SoftDeleteManager()  # Default manager (exclude deleted)
        all_objects = models.Manager()  # Include deleted
        
    # Queries
    Job.objects.all()  # Chỉ jobs chưa xóa
    Job.all_objects.all()  # Tất cả jobs (cả đã xóa)
    
    # Soft delete
    job.delete()  # Set is_deleted=True, deleted_at=now
    
    # Restore
    job.restore()  # Set is_deleted=False, deleted_at=None
    
    # Hard delete (permanent)
    job.hard_delete()  # Xóa vĩnh viễn
"""

from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    """Custom QuerySet to handle soft-deleted objects"""
    
    def delete(self):
        """Override delete to perform soft delete on queryset"""
        return self.update(
            is_deleted=True,
            deleted_at=timezone.now()
        )
    
    def hard_delete(self):
        """Permanently delete objects from database"""
        return super().delete()
    
    def alive(self):
        """Return only non-deleted objects"""
        return self.filter(is_deleted=False)
    
    def deleted(self):
        """Return only deleted objects"""
        return self.filter(is_deleted=True)
    
    def restore(self):
        """Restore soft-deleted objects"""
        return self.update(
            is_deleted=False,
            deleted_at=None
        )


class SoftDeleteManager(models.Manager):
    """
    Manager that automatically excludes soft-deleted objects
    
    Usage:
        Job.objects.all()  # Only non-deleted
        Job.objects.deleted()  # Only deleted
        Job.all_objects.all()  # All objects
    """
    
    def get_queryset(self):
        """Override default queryset to exclude deleted objects"""
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)
    
    def deleted(self):
        """Get only deleted objects"""
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=True)
    
    def with_deleted(self):
        """Get all objects including deleted"""
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteMixin(models.Model):
    """
    Abstract model mixin for soft delete functionality
    
    Adds fields:
        - is_deleted: Boolean flag
        - deleted_at: Timestamp when deleted
    
    Methods:
        - delete(): Soft delete (set is_deleted=True)
        - hard_delete(): Permanent delete
        - restore(): Un-delete object
    """
    
    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this object has been soft-deleted"
    )
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this object was soft-deleted"
    )
    
    # Default manager (excludes deleted)
    objects = SoftDeleteManager()
    
    # Manager that includes deleted objects
    all_objects = models.Manager()
    
    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False):
        """
        Soft delete: Set is_deleted=True instead of actually deleting
        
        Args:
            using: Database alias
            keep_parents: Whether to keep parent objects (ignored in soft delete)
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
    
    def hard_delete(self, using=None, keep_parents=False):
        """
        Permanently delete from database
        
        WARNING: This cannot be undone!
        """
        return super().delete(using=using, keep_parents=keep_parents)
    
    def restore(self):
        """
        Restore a soft-deleted object
        
        Returns:
            bool: True if restored, False if already active
        """
        if not self.is_deleted:
            return False
        
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])
        return True


# Example usage in admin.py
class SoftDeleteAdminMixin:
    """
    Admin mixin to show deleted objects and provide restore action
    
    Usage:
        from apps.core.soft_delete import SoftDeleteAdminMixin
        
        @admin.register(Job)
        class JobAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
            list_display = ['title', 'is_deleted', 'deleted_at']
            list_filter = ['is_deleted']
    """
    
    def get_queryset(self, request):
        """Show all objects including deleted in admin"""
        return self.model.all_objects.get_queryset()
    
    def delete_model(self, request, obj):
        """Override delete to use soft delete in admin"""
        obj.delete()
    
    def delete_queryset(self, request, queryset):
        """Override bulk delete to use soft delete"""
        queryset.update(is_deleted=True, deleted_at=timezone.now())
    
    # Add restore action
    def restore_objects(self, request, queryset):
        """Admin action to restore deleted objects"""
        count = queryset.filter(is_deleted=True).update(
            is_deleted=False,
            deleted_at=None
        )
        self.message_user(request, f"{count} objects restored successfully.")
    
    restore_objects.short_description = "Restore selected objects"
    
    # Add to actions
    actions = ['restore_objects', 'delete_selected']


# Utility functions
def cleanup_old_deleted_objects(model, days=90):
    """
    Permanently delete objects that were soft-deleted > X days ago
    
    Usage:
        # In management command or Celery task
        from apps.core.soft_delete import cleanup_old_deleted_objects
        from apps.jobs.models import Job
        
        cleanup_old_deleted_objects(Job, days=90)
    
    Args:
        model: Model class with SoftDeleteMixin
        days: Days threshold (default 90)
    
    Returns:
        int: Number of objects permanently deleted
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Get objects deleted more than X days ago
    old_deleted = model.all_objects.filter(
        is_deleted=True,
        deleted_at__lt=cutoff_date
    )
    
    count = old_deleted.count()
    old_deleted.hard_delete()
    
    return count
