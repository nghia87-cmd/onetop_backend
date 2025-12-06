from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .models import Application
from .serializers import ApplicationSerializer

class ApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'job']
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        
        # --- TỐI ƯU QUERY ---
        # select_related: Lấy luôn thông tin Job, Company của Job đó, và Ứng viên
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