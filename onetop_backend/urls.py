from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

# --- API VERSION CONFIGURATION ---
# Dynamic versioning - Dễ dàng thêm v2, v3 sau này
API_VERSION = 'v1'  # Default version

# App URLs - Reusable cho mọi version
app_urls = [
    path('auth/', include('apps.users.urls')),
    path('jobs/', include('apps.jobs.urls')),
    path('companies/', include('apps.companies.urls')),
    path('applications/', include('apps.applications.urls')),
    path('resumes/', include('apps.resumes.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('chats/', include('apps.chats.urls')),
    path('payments/', include('apps.payments.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- API Documentation (Swagger & Redoc) ---
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # --- API v1 (Current) ---
    path(f'api/v1/', include((app_urls, 'api'), namespace='v1')),
    
    # --- API v2 (Future) - Uncomment khi ready ---
    # path('api/v2/', include((app_urls_v2, 'api'), namespace='v2')),
]

# Cấu hình để phục vụ file media (ảnh đại diện, CV...) trong môi trường DEV
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)