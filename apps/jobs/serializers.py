from rest_framework import serializers
from .models import Job
from apps.companies.serializers import CompanySerializer

class JobSerializer(serializers.ModelSerializer):
    company_info = CompanySerializer(source='company', read_only=True)
    
    class Meta:
        model = Job
        fields = '__all__'
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at', 'views_count']