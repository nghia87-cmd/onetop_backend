from django.db import models
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from apps.core.models import TimeStampedModel
from apps.companies.models import Company

User = get_user_model()

class Job(TimeStampedModel):
    class JobType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Toàn thời gian'
        PART_TIME = 'PART_TIME', 'Bán thời gian'
        FREELANCE = 'FREELANCE', 'Freelance'
        INTERNSHIP = 'INTERNSHIP', 'Thực tập'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Nháp'
        PUBLISHED = 'PUBLISHED', 'Đang đăng'
        CLOSED = 'CLOSED', 'Đã đóng'

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    
    location = models.CharField(max_length=100) # Ví dụ: "Hà Nội", "Hồ Chí Minh"
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    
    # Mức lương (Có thể null nếu là Thỏa thuận)
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    is_negotiable = models.BooleanField(default=False) # Lương thỏa thuận

    description = models.TextField() # Mô tả công việc
    requirements = models.TextField() # Yêu cầu
    benefits = models.TextField() # Quyền lợi

    deadline = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    
    views_count = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Tạo slug dạng: tieu-de-cong-viec-8kytuID
            self.slug = f"{slugify(self.title)}-{str(self.id)[:8]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.company.name}"

class SavedJob(TimeStampedModel):
    """
    Bảng lưu việc làm đã thả tim (Bookmarks)
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_jobs')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='saved_by_users')

    class Meta:
        # Một người chỉ lưu 1 job 1 lần
        unique_together = ('user', 'job')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} saved {self.job.title}"