from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Resume


@receiver(pre_save, sender=Resume)
def ensure_single_primary_resume(sender, instance, **kwargs):
    """
    Signal: Đảm bảo chỉ có 1 CV primary cho mỗi user
    Khi set is_primary=True, tự động unset các CV khác của user đó
    """
    if instance.is_primary:
        # Unset tất cả CV primary khác của user này
        Resume.objects.filter(
            user=instance.user,
            is_primary=True
        ).exclude(
            pk=instance.pk  # Loại trừ chính CV đang save
        ).update(is_primary=False)
