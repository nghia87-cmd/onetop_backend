from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.payments'  # <--- BẮT BUỘC PHẢI CÓ 'apps.' ở trước
    verbose_name = "Quản lý thanh toán"