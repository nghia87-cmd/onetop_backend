from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Hiển thị các cột quan trọng ra list view
    list_display = ('email', 'full_name', 'user_type', 'is_active', 'date_joined', 'job_posting_credits')
    
    # Bộ lọc bên phải (giúp lọc nhanh User chưa kích hoạt)
    list_filter = ('user_type', 'is_active', 'groups')
    
    # Tìm kiếm theo email hoặc tên
    search_fields = ('email', 'full_name')
    
    ordering = ('-date_joined',)
    
    # Thêm các trường custom vào Form chỉnh sửa chi tiết
    fieldsets = UserAdmin.fieldsets + (
        ('Thông tin mở rộng (OneTop)', {
            'fields': (
                'user_type', 
                'full_name', 
                'avatar', 
                'job_posting_credits', 
                'membership_expires_at',
                'has_unlimited_posting',
                'can_view_contact'
            )
        }),
    )