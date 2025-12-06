from django.db import models
from django.utils.text import slugify
from apps.core.models import TimeStampedModel
from django.contrib.auth import get_user_model

User = get_user_model()

class Company(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
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