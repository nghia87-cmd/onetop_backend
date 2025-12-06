from rest_framework import viewsets, permissions, status
from rest_framework.exceptions import PermissionDenied, NotFound
from .models import Resume, WorkExperience, Education, Skill
from .serializers import (
    ResumeSerializer, 
    WorkExperienceSerializer, 
    EducationSerializer, 
    SkillSerializer
)

class ResumeViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Resume.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class BaseResumeItemViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset_model.objects.filter(resume__user=self.request.user)

    def perform_create(self, serializer):
        resume_id = self.request.data.get('resume')
        try:
            resume = Resume.objects.get(id=resume_id, user=self.request.user)
            serializer.save(resume=resume)
        except Resume.DoesNotExist:
            raise NotFound("Không tìm thấy CV hoặc bạn không có quyền sửa CV này.")

class WorkExperienceViewSet(BaseResumeItemViewSet):
    queryset_model = WorkExperience
    queryset = WorkExperience.objects.all()
    serializer_class = WorkExperienceSerializer

class EducationViewSet(BaseResumeItemViewSet):
    queryset_model = Education
    queryset = Education.objects.all()
    serializer_class = EducationSerializer

class SkillViewSet(BaseResumeItemViewSet):
    queryset_model = Skill
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer