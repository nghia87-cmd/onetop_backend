from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'  # <--- BẮT BUỘC PHẢI CÓ 'apps.' ở trước
    verbose_name = "Cốt lõi hệ thống"