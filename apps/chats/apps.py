from django.apps import AppConfig

class ChatsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.chats'  # <--- BẮT BUỘC PHẢI CÓ 'apps.' ở trước
    verbose_name = "Quản lý trò chuyện"