from django.apps import AppConfig

class CompaniesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.companies'  # <--- BẮT BUỘC PHẢI CÓ 'apps.' ở trước
    verbose_name = "Quản lý công ty"