from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction # <--- IMPORT QUAN TRỌNG

from .models import Application, InterviewSchedule
from .serializers import ApplicationSerializer, InterviewScheduleSerializer
from .tasks import send_interview_invitation_email
from apps.core.throttling import ApplicationSubmissionThrottle

class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'job']
    ordering_fields = ['created_at']
    
    def get_throttles(self):
        """Apply throttling only for create (submit application)"""
        if self.action == 'create':
            return [ApplicationSubmissionThrottle()]
        return super().get_throttles()

    def get_queryset(self):
        user = self.request.user
        
        # --- TỐI ƯU QUERY ---
        queryset = Application.objects.select_related('job', 'job__company', 'candidate')
        
        if user.user_type == 'CANDIDATE':
            return queryset.filter(candidate=user).order_by('-created_at')
            
        elif user.user_type == 'RECRUITER':
            return queryset.filter(job__company__owner=user).order_by('-created_at')
            
        return queryset.all()

    def perform_create(self, serializer):
        serializer.save(candidate=self.request.user)

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        application = self.get_object()
        
        if application.job.company.owner != request.user:
            return Response(
                {"detail": "Bạn không có quyền duyệt đơn này."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        status_val = request.data.get('status')
        note_val = request.data.get('note')

        if status_val:
            application.status = status_val
        if note_val is not None:
            application.note = note_val
            
        application.save()
        return Response(ApplicationSerializer(application).data)

# [VIEWSET MỚI] Quản lý lịch phỏng vấn
class InterviewScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = InterviewScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Tối ưu query: lấy luôn thông tin application và job liên quan
        queryset = InterviewSchedule.objects.select_related(
            'application', 'application__job', 'application__candidate'
        )

        if user.user_type == 'RECRUITER':
            # NTD xem lịch các đơn của mình
            return queryset.filter(application__job__company__owner=user)
        else:
            # Ứng viên xem lịch của mình
            return queryset.filter(application__candidate=user)

    def perform_create(self, serializer):
        # 1. Lấy ID đơn ứng tuyển từ request body
        # Hỗ trợ cả 2 key 'application' hoặc 'application_id' để tiện cho frontend
        application_id = self.request.data.get('application') 
        if not application_id:
            application_id = self.request.data.get('application_id')

        try:
            # Kiểm tra quyền: Chỉ chủ sở hữu Job mới được tạo lịch cho đơn này
            application = Application.objects.get(
                id=application_id, 
                job__company__owner=self.request.user
            )
        except Application.DoesNotExist:
            raise PermissionDenied("Đơn ứng tuyển không tồn tại hoặc bạn không có quyền lên lịch cho đơn này.")

        # [TỐI ƯU] Bắt đầu Transaction: Đảm bảo tính toàn vẹn dữ liệu
        with transaction.atomic():
            # 2. Lưu lịch phỏng vấn
            interview = serializer.save(application=application)
            
            # 3. Cập nhật trạng thái đơn ứng tuyển -> INTERVIEW
            application.status = 'INTERVIEW'
            application.save()

        # 4. Gửi email mời (Async - chạy ngầm)
        # QUAN TRỌNG: Để ngoài transaction để tránh việc Worker chạy trước khi DB commit xong
        if interview:
            send_interview_invitation_email.delay(interview.id)