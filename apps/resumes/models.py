from django.db import models
from apps.core.models import TimeStampedModel
from django.contrib.auth import get_user_model

User = get_user_model()

class Resume(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resumes')
    title = models.CharField(max_length=255, default="CV chưa đặt tên")
    
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True)
    
    file = models.FileField(upload_to='resumes/files/', null=True, blank=True)
    is_primary = models.BooleanField(default=False)

    # TRƯỜNG MỚI ĐỂ LƯU FILE PDF
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

class Education(TimeStampedModel):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='educations')
    school_name = models.CharField(max_length=255)
    major = models.CharField(max_length=255)
    degree = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

class Skill(TimeStampedModel):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    level = models.IntegerField(default=1)  # 1-5