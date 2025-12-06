from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.core.models import TimeStampedModel
from apps.jobs.models import Job
# [REFACTOR] Import validator chung để tránh lặp code
from apps.core.validators import validate_file_size

User = get_user_model()

class Application(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Chờ duyệt'
        VIEWED = 'VIEWED', 'Nhà tuyển dụng đã xem'
        INTERVIEW = 'INTERVIEW', 'Mời phỏng vấn'
        REJECTED = 'REJECTED', 'Từ chối'
        ACCEPTED = 'ACCEPTED', 'Đã trúng tuyển'

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    candidate = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    
    # [BẢO MẬT & NÂNG CẤP] Sử dụng validator đã import từ apps.core.validators
    cv_file = models.FileField(
        upload_to='applications/cvs/',
        help_text="Tải lên CV đính kèm (PDF, DOC, DOCX). Tối đa 5MB.",
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx']),
            validate_file_size 
        ]
    )
    
    cover_letter = models.TextField(blank=True, null=True)
    
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    
    note = models.TextField(
        blank=True, 
        null=True, 
        help_text="Ghi chú nội bộ của Nhà tuyển dụng về ứng viên này"
    )

    class Meta:
        # Một người không thể nộp 2 lần vào 1 job
        unique_together = ('job', 'candidate')
        # Sắp xếp đơn ứng tuyển mới nhất lên đầu
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.candidate.full_name} applied to {self.job.title}"

# [TÍNH NĂNG MỚI] Model Quản lý lịch phỏng vấn
class InterviewSchedule(TimeStampedModel):
    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Đã lên lịch'
        COMPLETED = 'COMPLETED', 'Đã hoàn thành'
        CANCELLED = 'CANCELLED', 'Đã hủy'

    application = models.OneToOneField(
        Application, 
        on_delete=models.CASCADE, 
        related_name='interview_schedule'
    )
    interview_date = models.DateTimeField(help_text="Thời gian bắt đầu phỏng vấn")
    duration_minutes = models.IntegerField(default=60, help_text="Thời lượng dự kiến (phút)")
    
    location = models.CharField(max_length=255, blank=True, help_text="Địa điểm offline (nếu có)")
    meeting_link = models.URLField(blank=True, null=True, help_text="Link họp online (Google Meet/Zoom)")
    
    interviewer = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='interviews_conducting',
        help_text="Người phỏng vấn (nếu có)"
    )
    
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.SCHEDULED
    )
    note = models.TextField(blank=True, help_text="Ghi chú cho ứng viên (VD: Mang theo laptop)")

    def __str__(self):
        return f"Phỏng vấn: {self.application.candidate.full_name} - {self.interview_date}"