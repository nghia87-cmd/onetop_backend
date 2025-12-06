from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'  # <--- BẮT BUỘC PHẢI CÓ 'apps.' ở trước
    label = 'users'
    verbose_name = "Quản lý người dùng"
    
    def ready(self):
        """Import signals when app is ready"""
        import apps.users.signals  # noqa