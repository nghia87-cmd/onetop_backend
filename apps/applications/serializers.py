from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from django.utils.translation import gettext_lazy as _
from .models import Application, InterviewSchedule
from apps.jobs.serializers import JobSerializer
from apps.jobs.models import Job
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
    
    def to_representation(self, instance):
        """
        CRITICAL FIX: Handle soft-deleted jobs in application history
        
        When a job is soft-deleted (is_deleted=True), we still need to show it in user's application history.
        Using instance.job_id (raw FK field) instead of instance.job (which returns None for soft-deleted jobs).
        """
        representation = super().to_representation(instance)
        
        # CRITICAL FIX: Use job_id (raw foreign key) instead of job object
        # instance.job returns None if job is soft-deleted (SoftDeleteManager filters it out)
        # but instance.job_id always contains the actual ID from database
        if instance.job_id:
            try:
                # Use all_objects to include soft-deleted jobs
                job = Job.all_objects.get(pk=instance.job_id)
                representation['job_info'] = JobSerializer(job).data
                
                # Add flag to indicate if job was deleted (for frontend to show "This job is no longer available")
                representation['job_info']['is_deleted'] = job.is_deleted
                
            except Job.DoesNotExist:
                # Fallback: Job was hard-deleted (very rare)
                representation['job_info'] = {
                    'title': '[Công việc đã bị xóa vĩnh viễn]',
                    'is_deleted': True,
                    'company': {'name': 'N/A'}
                }
        
        return representation