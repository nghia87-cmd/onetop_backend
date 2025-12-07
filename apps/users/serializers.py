from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.mail import send_mail
from django.conf import settings
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'phone_number', 'avatar', 'user_type', 'job_posting_credits', 'membership_expires_at']
        # [BẢO MẬT] Giữ nguyên các trường read_only như lần trước
        read_only_fields = ['id', 'email', 'date_joined', 'job_posting_credits', 'membership_expires_at', 'user_type']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'full_name', 'user_type', 'phone_number']

    def create(self, validated_data):
        user_type = validated_data.get('user_type')
        
        # [LOGIC KIỂM DUYỆT] 
        # Mặc định tạo user là Active. 
        # Nếu là RECRUITER -> set is_active=False (Chờ duyệt)
        is_active = True
        if user_type == 'RECRUITER':
            is_active = False

        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['email'],  # Username = Email (no separate username field)
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            phone_number=validated_data.get('phone_number', ''),  # CRITICAL FIX: Save phone_number
            user_type=user_type,
            is_active=is_active # <-- Tham số quan trọng
        )
        
        # CRITICAL FIX #5: Async email để không làm chậm API (1-3 giây SMTP connection)
        # Chuyển sang Celery task thay vì send_mail đồng bộ
        if user_type == 'RECRUITER' and not is_active:
            from apps.users.tasks import send_welcome_email_task
            # Delay task để không block response
            send_welcome_email_task.delay(
                user_id=user.id,
                user_email=user.email,
                user_full_name=user.full_name
            )
        
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Hàm này của simplejwt đã tự động check user.is_active
        # Nếu is_active=False, nó sẽ raise exception: "No active account found with the given credentials"
        data = super().validate(attrs)
        
        data['user_id'] = self.user.id
        data['full_name'] = self.user.full_name
        data['email'] = self.user.email
        data['user_type'] = self.user.user_type
        data['avatar'] = self.user.avatar.url if self.user.avatar else None
        return data