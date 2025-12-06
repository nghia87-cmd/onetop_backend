from django.db import models
from django.contrib.auth import get_user_model
from apps.core.models import TimeStampedModel

User = get_user_model()

class ServicePackage(TimeStampedModel):
    class PackageType(models.TextChoices):
        CREDIT = 'CREDIT', 'Gói mua lượt (Credits)'
        SUBSCRIPTION = 'SUBSCRIPTION', 'Gói thuê bao (Subscription)'

    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    duration_days = models.IntegerField(default=30)
    
    # Phân loại gói
    package_type = models.CharField(
        max_length=20, 
        choices=PackageType.choices, 
        default=PackageType.CREDIT
    )

    # Số lượt cộng thêm (Dùng cho gói CREDIT)
    job_posting_limit = models.IntegerField(default=0) 
    
    # --- Các quyền lợi VIP (Dùng cho gói SUBSCRIPTION) ---
    allow_unlimited_posting = models.BooleanField(default=False) # Đăng tin không giới hạn
    allow_view_contact = models.BooleanField(default=False)      # Xem liên hệ ứng viên

    description = models.TextField(blank=True)

    def __str__(self):
        # Hiển thị tên kèm loại gói trong Admin cho dễ nhìn
        return f"{self.name} ({self.get_package_type_display()}) - {self.price:,.0f} đ"

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
        return f"{self.user.email} - {self.amount:,.0f} - {self.status}"