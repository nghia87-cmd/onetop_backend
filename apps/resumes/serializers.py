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

    # --- QUAN TRỌNG: Hàm này phải thụt vào trong class ResumeSerializer ---
    def to_representation(self, instance):
        """
        Ghi đè hàm này để ẩn thông tin nếu người xem không có quyền
        """
        data = super().to_representation(instance)
        request = self.context.get('request')
        
        # Nếu là chủ sở hữu CV thì luôn thấy
        if request and request.user == instance.user:
            return data

        # Nếu là NTD: Check quyền
        if request and request.user.user_type == 'RECRUITER':
            if not request.user.can_view_contact:
                data['email'] = '******** (Nâng cấp VIP để xem)'
                data['phone'] = '******** (Nâng cấp VIP để xem)'
                # Ẩn thêm file đính kèm nếu muốn
                data['file'] = None
        
        return data