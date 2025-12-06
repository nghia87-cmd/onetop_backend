from django.db import models
from django.utils.text import slugify
from apps.core.models import TimeStampedModel
from apps.core.soft_delete import SoftDeleteMixin
from django.contrib.auth import get_user_model

User = get_user_model()

class Company(SoftDeleteMixin, TimeStampedModel):
    # Remove unique=True - sẽ dùng UniqueConstraint bên dưới
    name = models.CharField(max_length=255)
    slug = models.SlugField(
        max_length=255,
        blank=True,
        db_index=True  # INDEX: SEO-friendly URLs, hay query theo slug
    )
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    website = models.URLField(max_length=200, blank=True)
    description = models.TextField()
    address = models.CharField(max_length=500)
    
    # Người sở hữu công ty
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_companies')
    
    employee_count = models.CharField(max_length=50, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Companies"
        
        # FIX: Unique constraint chỉ áp dụng cho active records
        # Cho phép tạo lại Company cùng tên sau khi soft delete
        constraints = [
            models.UniqueConstraint(
                fields=['name'],
                condition=models.Q(is_deleted=False),
                name='unique_active_company_name'
            ),
            models.UniqueConstraint(
                fields=['slug'],
                condition=models.Q(is_deleted=False),
                name='unique_active_company_slug'
            ),
        ]