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
        fields = ['id', 'email', 'full_name', 'avatar', 'user_type', 'job_posting_credits', 'membership_expires_at']
        # [BẢO MẬT] Giữ nguyên các trường read_only như lần trước
        read_only_fields = ['id', 'email', 'date_joined', 'job_posting_credits', 'membership_expires_at', 'user_type']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'full_name', 'user_type']

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
            username=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            user_type=user_type,
            is_active=is_active # <-- Tham số quan trọng
        )
        
        # CRITICAL FIX: Send email notification for RECRUITER registration (UX improvement)
        if user_type == 'RECRUITER' and not is_active:
            try:
                send_mail(
                    subject=str(_('Account Registration - Pending Approval')),
                    message=_(
                        "Hello {name},\n\n"
                        "Thank you for registering as a Recruiter on OneTop.\n\n"
                        "Your account is currently pending approval by our admin team. "
                        "You will receive another email once your account has been approved and you can start posting jobs.\n\n"
                        "This process usually takes 1-2 business days.\n\n"
                        "Best regards,\nOneTop Team"
                    ).format(name=user.full_name),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception as e:
                # Don't fail registration if email fails
                import logging
                logging.getLogger(__name__).error(f"Failed to send registration email to {user.email}: {e}")
        
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