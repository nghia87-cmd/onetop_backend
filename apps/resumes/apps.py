from django.apps import AppConfig


class ResumesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.resumes'  # <--- BẮT BUỘC PHẢI CÓ 'apps.' ở trước
    verbose_name = "Quản lý hồ sơ"

    def ready(self):
        # Đảm bảo Celery đăng ký task khi ứng dụng khởi động
        import apps.resumes.tasks