# apps/jobs/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JobViewSet, SavedJobViewSet

router = DefaultRouter()
router.register(r'', JobViewSet, basename='job')  # Fixed: Use empty string for cleaner URLs
router.register(r'saved', SavedJobViewSet, basename='saved-jobs')

urlpatterns = [
    path('', include(router.urls)),
]