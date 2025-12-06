from rest_framework import viewsets, permissions, filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q
from .models import Job, SavedJob
from .serializers import JobSerializer, SavedJobSerializer
from apps.resumes.models import Resume

class JobViewSet(viewsets.ModelViewSet):
    # Tối ưu N+1 Query: Lấy luôn thông tin công ty
    queryset = Job.objects.select_related('company').filter(status='PUBLISHED').order_by('-created_at')
    
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['job_type', 'location', 'company']
    search_fields = ['title', 'description', 'requirements']
    ordering_fields = ['created_at', 'salary_max', 'views_count']

    def perform_create(self, serializer):
        user = self.request.user
        
        # 1. Lấy thông tin company từ dữ liệu gửi lên
        company = serializer.validated_data.get('company')

        # 2. Kiểm tra quyền sở hữu (Chặn đăng tin hộ công ty khác)
        if company and company.owner != user:
            raise PermissionDenied("Bạn không có quyền đăng tin cho công ty này.")

        # 3. Logic kiểm tra quyền lợi (VIP/Credit)
        if user.user_type == 'RECRUITER':
            # Check hạn sử dụng
            if not user.membership_expires_at or user.membership_expires_at < timezone.now():
                 raise PermissionDenied("Gói dịch vụ đã hết hạn. Vui lòng gia hạn.")
            
            # Check quyền đăng tin
            if user.has_unlimited_posting:
                pass # VIP thì không bị trừ lượt
            else:
                # Không phải VIP thì phải có Credits
                if user.job_posting_credits <= 0:
                    raise PermissionDenied("Bạn đã hết lượt đăng tin. Vui lòng mua thêm gói.")
                
                # Trừ 1 lượt
                user.job_posting_credits -= 1
                user.save()

        # 4. Lưu Job
        serializer.save()

    @action(detail=False, methods=['get'], url_path='recommendations')
    def recommendations(self, request):
        """
        Gợi ý việc làm dựa trên CV chính của ứng viên.
        """
        user = request.user
        if user.user_type != 'CANDIDATE':
            return Response({"detail": "Chỉ dành cho ứng viên."}, status=403)

        # Lấy CV chính hoặc CV mới nhất
        resume = Resume.objects.filter(user=user, is_primary=True).first()
        if not resume:
            resume = Resume.objects.filter(user=user).order_by('-created_at').first()
        
        if not resume:
            return Response({"detail": "Bạn cần tạo hồ sơ (CV) trước."}, status=400)

        # Lấy kỹ năng từ CV
        user_skills = resume.skills.values_list('name', flat=True)
        
        # Tìm Job phù hợp
        query = Q()
        if resume.title:
            query |= Q(title__icontains=resume.title)
        for skill in user_skills:
            query |= Q(requirements__icontains=skill) | Q(description__icontains=skill)

        # Tối ưu query ở đây luôn
        recommended_jobs = Job.objects.select_related('company').filter(
            status='PUBLISHED'
        ).filter(query).distinct().order_by('-created_at')[:10]

        serializer = self.get_serializer(recommended_jobs, many=True)
        return Response(serializer.data)
    
class SavedJobViewSet(viewsets.ModelViewSet):
    """
    API Quản lý việc làm đã lưu.
    - GET /: Xem danh sách đã lưu
    - POST /: Lưu việc làm (Body: {"job": 1})
    - DELETE /{id}/: Bỏ lưu
    """
    serializer_class = SavedJobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Chỉ lấy danh sách của user đang login
        return SavedJob.objects.filter(user=self.request.user).select_related('job', 'job__company')

    def perform_create(self, serializer):
        # Tự động gán user
        serializer.save(user=self.request.user)