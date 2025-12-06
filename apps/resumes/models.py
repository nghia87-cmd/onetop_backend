from django.db import models
from django.core.validators import FileExtensionValidator
from django.contrib.auth import get_user_model
from apps.core.models import TimeStampedModel
# Import validator chung từ core (đảm bảo bạn đã tạo file apps/core/validators.py)
from apps.core.validators import validate_file_size 

User = get_user_model()

class Resume(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    title = models.CharField(max_length=255, default="CV chưa đặt tên")
    
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True)
    
    # [BẢO MẬT] Thêm validators để kiểm soát file đầu vào
    file = models.FileField(
        upload_to='resumes/files/',
        null=True, 
        blank=True,
        help_text="Tải lên CV đính kèm (PDF, DOC, DOCX, ảnh). Tối đa 5MB.",
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']),
            validate_file_size # Sử dụng hàm đã import
        ]
    )
    
    is_primary = models.BooleanField(default=False)

    # File PDF được hệ thống tạo ra
    pdf_file = models.FileField(
        upload_to='resumes/pdf_output/', 
        null=True, 
        blank=True, 
        verbose_name="Generated PDF File"
    )

    def __str__(self):
        return f"{self.title} - {self.user.email}"

# --- Các thành phần con của CV ---

class WorkExperience(TimeStampedModel):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='experiences')
    company_name = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_date']

class Education(TimeStampedModel):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='educations')
    school_name = models.CharField(max_length=255)
    major = models.CharField(max_length=255)
    degree = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-start_date']

class Skill(TimeStampedModel):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    level = models.IntegerField(default=1)  # 1-5