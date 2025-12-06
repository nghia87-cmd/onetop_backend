from rest_framework import serializers
from .models import Resume, WorkExperience, Education, Skill

class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        fields = '__all__'
        read_only_fields = ['resume']

class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = '__all__'
        read_only_fields = ['resume']

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = '__all__'
        read_only_fields = ['resume']

class ResumeSerializer(serializers.ModelSerializer):
    experiences = WorkExperienceSerializer(many=True, read_only=True)
    educations = EducationSerializer(many=True, read_only=True)
    skills = SkillSerializer(many=True, read_only=True)

    class Meta:
        model = Resume
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']