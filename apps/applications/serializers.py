from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from django.utils.translation import gettext_lazy as _
from .models import Application, InterviewSchedule
from apps.jobs.serializers import JobSerializer
from apps.users.serializers import UserSerializer

# [TÍNH NĂNG MỚI] Serializer cho lịch phỏng vấn
class InterviewScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSchedule
        fields = '__all__'
        read_only_fields = ['application'] # Application ID sẽ được gán tự động trong View

class ApplicationSerializer(serializers.ModelSerializer):
    # Nhúng thông tin Job và Candidate để Frontend hiển thị chi tiết
    job_info = JobSerializer(source='job', read_only=True)
    candidate_info = UserSerializer(source='candidate', read_only=True)
    
    # [TÍNH NĂNG MỚI] Nhúng thông tin lịch phỏng vấn (nếu có) vào response
    interview_schedule = InterviewScheduleSerializer(read_only=True)

    class Meta:
        model = Application
        fields = '__all__'
        read_only_fields = ['id', 'candidate', 'created_at', 'updated_at', 'status']
        
        # Validate: Đảm bảo 1 người không nộp 2 lần cho 1 job ngay tại Serializer
        validators = [
            UniqueTogetherValidator(
                queryset=Application.objects.all(),
                fields=['job', 'candidate'],
                message=_('You have already applied for this job.')
            )
        ]