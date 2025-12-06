from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message
from apps.users.serializers import UserSerializer

User = get_user_model()

class MessageSerializer(serializers.ModelSerializer):
    sender_info = UserSerializer(source='sender', read_only=True)

    class Meta:
        model = Message
        fields = '__all__'

class ConversationSerializer(serializers.ModelSerializer):
    partner = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'job', 'partner', 'last_message', 'last_message_at']

    def get_partner(self, obj):
        user = self.context['request'].user
        if obj.participant1 == user:
            return UserSerializer(obj.participant2).data
        return UserSerializer(obj.participant1).data

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return MessageSerializer(last_msg).data
        return None