from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ResumeViewSet, 
    WorkExperienceViewSet, 
    EducationViewSet, 
    SkillViewSet
)

router = DefaultRouter()
router.register(r'list', ResumeViewSet, basename='resume')
router.register(r'experiences', WorkExperienceViewSet, basename='experience')
router.register(r'educations', EducationViewSet, basename='education')
router.register(r'skills', SkillViewSet, basename='skill')

urlpatterns = [
    path('', include(router.urls)),
]