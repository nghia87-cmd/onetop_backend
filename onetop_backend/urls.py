from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- API Documentation (Swagger & Redoc) ---
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # --- Include Apps URLs ---
    path('api/v1/auth/', include('apps.users.urls')),
    path('api/v1/jobs/', include('apps.jobs.urls')),
    path('api/v1/companies/', include('apps.companies.urls')),
    path('api/v1/applications/', include('apps.applications.urls')),
    path('api/v1/resumes/', include('apps.resumes.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/chats/', include('apps.chats.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
]

# Cấu hình để phục vụ file media (ảnh đại diện, CV...) trong môi trường DEV
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)