# apps/jobs/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JobViewSet, SavedJobViewSet # <--- Import thêm

router = DefaultRouter()
router.register(r'list', JobViewSet) # Đổi path cũ r'' thành r'list' cho rõ nghĩa hoặc giữ nguyên tùy bạn
router.register(r'saved', SavedJobViewSet, basename='saved-jobs') # <--- Thêm dòng này

urlpatterns = [
    path('', include(router.urls)),
]