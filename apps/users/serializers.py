from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'avatar', 'user_type', 'job_posting_credits', 'membership_expires_at']
        read_only_fields = ['id', 'email', 'date_joined']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'full_name', 'user_type']

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            user_type=validated_data['user_type']
        )
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user_id'] = self.user.id
        data['full_name'] = self.user.full_name
        data['email'] = self.user.email
        data['user_type'] = self.user.user_type
        data['avatar'] = self.user.avatar.url if self.user.avatar else None
        return data