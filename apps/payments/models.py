from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import TimeStampedModel

User = get_user_model()

class ServicePackage(TimeStampedModel):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    duration_days = models.IntegerField(default=30)
    job_posting_limit = models.IntegerField(default=5)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.price} đ"

class Transaction(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Chờ thanh toán'
        SUCCESS = 'SUCCESS', 'Thành công'
        FAILED = 'FAILED', 'Thất bại'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    package = models.ForeignKey(ServicePackage, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.user.email} - {self.amount} - {self.status}"