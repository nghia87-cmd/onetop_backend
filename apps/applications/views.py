from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .models import Application
from .serializers import ApplicationSerializer

class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'job']
    ordering_fields = ['created_at']

    def get_queryset(self):
        """
        Phân quyền dữ liệu (Data Privacy):
        - Nếu là Ứng viên (CANDIDATE): Chỉ xem đơn của chính mình.
        - Nếu là NTD (RECRUITER): Xem tất cả đơn nộp vào các Job thuộc công ty mình sở hữu.
        """
        user = self.request.user
        
        if user.user_type == 'CANDIDATE':
            return Application.objects.filter(candidate=user).order_by('-created_at')
            
        elif user.user_type == 'RECRUITER':
            # Lấy tất cả job của các công ty do user này sở hữu
            return Application.objects.filter(job__company__owner=user).order_by('-created_at')
            
        # Admin thấy hết
        return Application.objects.all()

    def perform_create(self, serializer):
        # Tự động gán người nộp đơn là User đang login
        serializer.save(candidate=self.request.request.user)

    @action(detail=True, methods=['patch'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        Custom API cho NTD cập nhật trạng thái đơn (Duyệt/Từ chối)
        URL: PATCH /api/v1/applications/{id}/update-status/
        Body: { "status": "INTERVIEW", "note": "Hẹn phỏng vấn thứ 6" }
        """
        application = self.get_object()
        
        # Chỉ chủ sở hữu Job mới được đổi trạng thái đơn
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