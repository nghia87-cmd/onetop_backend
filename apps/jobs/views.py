from rest_framework import viewsets, permissions, filters
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Job
from .serializers import JobSerializer

class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.filter(status='PUBLISHED').order_by('-created_at')
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['job_type', 'location', 'company']
    search_fields = ['title', 'description', 'requirements']
    ordering_fields = ['created_at', 'salary_max', 'views_count']

    def perform_create(self, serializer):
        user = self.request.user
        company = serializer.validated_data.get('company')

        if company and company.owner != user:
            raise PermissionDenied("Bạn không có quyền đăng tin cho công ty này vì bạn không phải là chủ sở hữu.")

        if user.user_type == 'RECRUITER':
            if not user.membership_expires_at or user.membership_expires_at < timezone.now():
                 raise PermissionDenied("Gói dịch vụ của bạn đã hết hạn hoặc chưa đăng ký.")
            
            if user.job_posting_credits <= 0:
                 raise PermissionDenied("Bạn đã hết lượt đăng tin. Vui lòng mua thêm gói dịch vụ.")

            user.job_posting_credits -= 1
            user.save()

        serializer.save(owner=user)