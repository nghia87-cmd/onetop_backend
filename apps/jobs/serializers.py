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