from django.db import models
from apps.core.models import TimeStampedModel
from django.contrib.auth import get_user_model
from apps.jobs.models import Job

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
    
    # Link tới CV (Tạm thời để FileField)
    cv_file = models.FileField(upload_to='applications/cvs/') 
    cover_letter = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    note = models.TextField(blank=True, null=True) # Ghi chú của NTD về ứng viên này

    class Meta:
        # Một người không thể nộp 2 lần vào 1 job
        unique_together = ('job', 'candidate')

    def __str__(self):
        return f"{self.candidate.full_name} applied to {self.job.title}"