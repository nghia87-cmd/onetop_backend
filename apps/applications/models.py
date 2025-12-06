from django.db import models
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.core.models import TimeStampedModel
from apps.jobs.models import Job

User = get_user_model()

# --- Validator: Kiểm tra dung lượng file (Có thể tách ra file utils.py dùng chung) ---
def validate_file_size(value):
    limit = 5 * 1024 * 1024  # Giới hạn 5 MB
    if value.size > limit:
        raise ValidationError('Dung lượng file quá lớn. Vui lòng tải lên file nhỏ hơn 5MB.')

class Application(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Chờ duyệt'
        VIEWED = 'VIEWED', 'Nhà tuyển dụng đã xem'
        INTERVIEW = 'INTERVIEW', 'Mời phỏng vấn'
        REJECTED = 'REJECTED', 'Từ chối'
        ACCEPTED = 'ACCEPTED', 'Đã trúng tuyển'

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    candidate = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    
    # [BẢO MẬT & NÂNG CẤP] Thêm validator cho file CV
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