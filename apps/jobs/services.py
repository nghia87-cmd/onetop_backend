"""
Job Service Layer
Xử lý business logic liên quan đến Job posting
"""
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from django.db.models import F
from django.db import transaction  # CRITICAL FIX: For atomicity
import logging

from .models import Job
from apps.companies.models import Company

logger = logging.getLogger(__name__)


class JobService:
    """Service xử lý logic tạo và quản lý Job"""
    
    @staticmethod
    def validate_job_posting_permission(user, company):
        """
        Validate quyền đăng tin việc làm
        
        Args:
            user: User object (RECRUITER)
            company: Company object
            
        Raises:
            PermissionDenied: Nếu không đủ quyền hoặc hết credits
            
        Returns:
            bool: True nếu validate thành công
        """
        # 1. Kiểm tra sở hữu công ty
        if company and company.owner != user:
            raise PermissionDenied(_("You do not have permission to post jobs for this company."))
        
        # 2. Chỉ RECRUITER mới được đăng tin
        if user.user_type != 'RECRUITER':
            raise PermissionDenied(_("Only recruiters can post jobs."))
        
        # 3. Check hạn sử dụng gói dịch vụ
        if not user.membership_expires_at or user.membership_expires_at < timezone.now():
            raise PermissionDenied(_("Your service package has expired. Please renew."))
        
        # 4. Check quyền đăng tin (VIP unlimited hoặc trừ credits)
        if not user.has_unlimited_posting:
            if user.job_posting_credits <= 0:
                raise PermissionDenied(_('You have run out of job posting credits. Please purchase a package.'))
        
        return True
    
    @staticmethod
    def create_job(user, validated_data):
        """
        Tạo Job mới và xử lý trừ credits nếu cần
        
        Args:
            user: User object
            validated_data: Data đã validate từ serializer
            
        Returns:
            Job: Job object đã tạo
        """
        company = validated_data.get('company')
        
        # Validate quyền
        JobService.validate_job_posting_permission(user, company)
        
        # CRITICAL FIX: Wrap trong transaction.atomic() để tránh mất tiền nếu tạo Job thất bại
        # Nếu Job.objects.create() lỗi (constraint, trigger, timeout), credits sẽ ROLLBACK
        with transaction.atomic():
            # Trừ credits nếu không phải VIP (sử dụng F() để atomic update)
            # Số credit trừ lấy từ settings (có thể config khuyến mãi)
            if not user.has_unlimited_posting:
                from apps.users.models import User
                
                credit_cost = getattr(settings, 'JOB_POSTING_CREDIT_COST', 1)
                
                # Atomic decrement với version increment cho Optimistic Locking
                # Phải tăng version để PaymentService detect được thay đổi credits
                updated = User.objects.filter(
                    pk=user.pk,
                    job_posting_credits__gte=credit_cost  # Đảm bảo đủ credits
                ).update(
                    job_posting_credits=F('job_posting_credits') - credit_cost,
                    version=F('version') + 1  # REQUIRED: Increment version for optimistic locking
                )
                
                if not updated:
                    # Double-check nếu credits vừa hết (concurrent requests)
                    raise PermissionDenied(_('You have run out of job posting credits. Please purchase a package.'))
                
                # Refresh để lấy credits mới
                user.refresh_from_db()
                logger.info(f"User {user.id} credits after posting: {user.job_posting_credits}")
            
            # Tạo job TRONG CÙNG TRANSACTION - nếu lỗi, credits sẽ rollback
            job = Job.objects.create(**validated_data)
        
        logger.info(f"Job {job.id} created by user {user.id} (company: {company.name if company else 'N/A'})")
        return job
    
    @staticmethod
    def update_job(job, user, validated_data):
        """
        Cập nhật Job (chỉ owner được phép)
        
        Args:
            job: Job object cần update
            user: User thực hiện request
            validated_data: Data mới
            
        Returns:
            Job: Job đã update
        """
        # Kiểm tra ownership
        if job.company and job.company.owner != user:
            raise PermissionDenied(_("You do not have permission to edit this job."))
        
        # Update fields
        for attr, value in validated_data.items():
            setattr(job, attr, value)
        
        job.save()
        logger.info(f"Job {job.id} updated by user {user.id}")
        return job
    
    @staticmethod
    def delete_job(job, user):
        """
        Xóa Job (Soft Delete - chỉ đánh dấu is_deleted=True)
        
        Args:
            job: Job object cần xóa
            user: User thực hiện request
            
        Note:
            Sử dụng Soft Delete để:
            - Khôi phục dữ liệu nếu cần
            - Audit trail (biết ai xóa khi nào)
            - Tuân thủ quy định lưu trữ dữ liệu
            
            Để xóa vĩnh viễn: job.hard_delete()
        """
        # Kiểm tra ownership
        if job.company and job.company.owner != user:
            raise PermissionDenied(_("You do not have permission to delete this job."))
        
        # Soft Delete (inherited from SoftDeleteMixin)
        job.delete()  # Set is_deleted=True, deleted_at=now
        
        logger.info(f"Job {job.id} soft-deleted by user {user.id} at {job.deleted_at}")
    
    @staticmethod
    def restore_job(job, user):
        """
        Khôi phục Job đã xóa (Soft Delete)
        
        Args:
            job: Job object đã bị xóa
            user: User thực hiện restore
            
        Returns:
            bool: True if restored, False if already active
        """
        # Kiểm tra ownership
        if job.company and job.company.owner != user:
            raise PermissionDenied(_("You do not have permission to restore this job."))
        
        restored = job.restore()
        
        if restored:
            logger.info(f"Job {job.id} restored by user {user.id}")
        
        return restored

