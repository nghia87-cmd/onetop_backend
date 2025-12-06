from django.apps import AppConfig

class JobsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.jobs'  # <--- BẮT BUỘC PHẢI CÓ 'apps.' ở trước
    verbose_name = "Quản lý công việc"