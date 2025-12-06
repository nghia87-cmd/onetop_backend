from django.db import models
from django.utils.text import slugify
from apps.core.models import TimeStampedModel
from apps.companies.models import Company

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
    
    location = models.CharField(max_length=100)
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    
    salary_min = models.IntegerField(null=True, blank=True)
    salary_max = models.IntegerField(null=True, blank=True)
    is_negotiable = models.BooleanField(default=False)

    description = models.TextField()
    requirements = models.TextField()
    benefits = models.TextField()

    deadline = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PUBLISHED)
    
    views_count = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"{slugify(self.title)}-{str(self.id)[:8]}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.company.name}"