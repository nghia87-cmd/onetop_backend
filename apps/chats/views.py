from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # --- TỐI ƯU QUERY ---
        # Load sẵn thông tin 2 người tham gia và thông tin Job
        return Conversation.objects.select_related(
            'participant1', 'participant2', 'job'
        ).filter(
            Q(participant1=user) | Q(participant2=user)
        ).order_by('-last_message_at')

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        conversation = self.get_object()
        if request.user not in [conversation.participant1, conversation.participant2]:
            return Response(status=status.HTTP_403_FORBIDDEN)
            
        # Load sẵn thông tin người gửi để hiển thị avatar/tên
        messages = conversation.messages.select_related('sender').all().order_by('created_at')
        
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)