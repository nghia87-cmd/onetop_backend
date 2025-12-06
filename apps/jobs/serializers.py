from rest_framework import serializers
from .models import Job, SavedJob
from apps.companies.serializers import CompanySerializer

class JobSerializer(serializers.ModelSerializer):
    company_info = CompanySerializer(source='company', read_only=True)
    
    class Meta:
        model = Job
        fields = '__all__'
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'views_count']

class SavedJobSerializer(serializers.ModelSerializer):
    # Nhúng thông tin Job vào để hiển thị luôn
    job_info = JobSerializer(source='job', read_only=True)

    class Meta:
        model = SavedJob
        fields = ['id', 'user', 'job', 'job_info', 'created_at']
        read_only_fields = ['user']
    
    # CRITICAL FIX #2: Handle soft-deleted jobs for UX consistency
    # Giống logic trong ApplicationSerializer - tránh SavedJob "bay màu" khi Job bị xóa mềm
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # Xử lý trường hợp Job bị Soft Delete
        if instance.job_id:
            try:
                # Dùng all_objects để lấy cả job đã xóa mềm
                job = Job.all_objects.get(pk=instance.job_id)
                representation['job_info'] = JobSerializer(job).data
                representation['job_info']['is_deleted'] = job.is_deleted
                
                # Frontend có thể hiển thị badge "Đã xóa" hoặc disable actions
            except Job.DoesNotExist:
                # Job bị xóa cứng (hard delete) - rất hiếm xảy ra
                representation['job_info'] = {
                    'id': instance.job_id,
                    'title': 'Job not found',
                    'is_deleted': True
                }
        
        return representation