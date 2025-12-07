from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from apps.core.views import download_resume_pdf, download_application_cv, WebSocketTicketView

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
    
    # --- WebSocket Ticket (One-time auth) ---
    path('api/v1/ws-ticket/', WebSocketTicketView.as_view(), name='ws-ticket'),
    
    # --- Secure Media Downloads (Protected Files) ---
    path('api/v1/media/resume/<uuid:resume_id>/download/', download_resume_pdf, name='download-resume-pdf'),
    path('api/v1/media/application/<uuid:application_id>/download/', download_application_cv, name='download-application-cv'),
    
    # --- API v2 (Future) - Uncomment khi ready ---
    # path('api/v2/', include((app_urls_v2, 'api'), namespace='v2')),
]

# WARNING: In production, DO NOT serve media files directly via Django
# Use Nginx with X-Accel-Redirect for protected files
if settings.DEBUG:
    # Development only - serve static/media files
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Media files served directly in dev (will be protected via Nginx in production)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)