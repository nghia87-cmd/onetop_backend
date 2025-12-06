from rest_framework import viewsets, permissions, filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q
from .models import Job
from .serializers import JobSerializer
from apps.resumes.models import Resume

class JobViewSet(viewsets.ModelViewSet):
    # Tối ưu: Dùng select_related để giảm số lượng query xuống DB
    queryset = Job.objects.select_related('company').filter(status='PUBLISHED').order_by('-created_at')
    
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['job_type', 'location', 'company']
    search_fields = ['title', 'description', 'requirements']
    ordering_fields = ['created_at', 'salary_max', 'views_count']

    def perform_create(self, serializer):
        user = self.request.user
        
        # Lấy thông tin company từ dữ liệu gửi lên
        company = serializer.validated_data.get('company')

        # Kiểm tra quyền: Chỉ chủ sở hữu mới được đăng tin cho công ty đó
        if company and company.owner != user:
            raise PermissionDenied("Bạn không có quyền đăng tin cho công ty này.")

        # Logic trừ tiền (Credits) của Nhà tuyển dụng
        if user.user_type == 'RECRUITER':
            if not user.membership_expires_at or user.membership_expires_at < timezone.now():
                 raise PermissionDenied("Gói dịch vụ đã hết hạn. Vui lòng gia hạn.")
            
            if user.job_posting_credits <= 0:
                 raise PermissionDenied("Bạn đã hết lượt đăng tin. Vui lòng mua thêm gói.")

            user.job_posting_credits -= 1
            user.save()

        # Lưu Job (Không cần truyền owner vì Job gắn với Company)
        serializer.save()

    @action(detail=False, methods=['get'], url_path='recommendations')
    def recommendations(self, request):
        """
        Gợi ý việc làm phù hợp dựa trên CV chính của ứng viên.
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
        
        # Tìm Job phù hợp (Match title hoặc skills)
        query = Q()
        if resume.title:
            query |= Q(title__icontains=resume.title)
        for skill in user_skills:
            query |= Q(requirements__icontains=skill) | Q(description__icontains=skill)

        # Tối ưu: Dùng select_related ở đây nữa
        recommended_jobs = Job.objects.select_related('company').filter(
            status='PUBLISHED'
        ).filter(query).distinct().order_by('-created_at')[:10]

        serializer = self.get_serializer(recommended_jobs, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        user = self.request.user
        company = serializer.validated_data.get('company')

        if company and company.owner != user:
            raise PermissionDenied("Bạn không có quyền đăng tin cho công ty này.")

        # Logic kiểm tra quyền lợi
        if user.user_type == 'RECRUITER':
            # 1. Check hạn sử dụng
            if not user.membership_expires_at or user.membership_expires_at < timezone.now():
                 raise PermissionDenied("Gói dịch vụ đã hết hạn. Vui lòng gia hạn.")
            
            # 2. Check quyền đăng tin
            if user.has_unlimited_posting:
                pass # VIP thì không bị trừ tiền, cứ thế đăng
            else:
                # Không phải VIP thì phải có Credits
                if user.job_posting_credits <= 0:
                    raise PermissionDenied("Bạn đã hết lượt đăng tin. Vui lòng mua thêm gói.")
                
                # Trừ 1 lượt
                user.job_posting_credits -= 1
                user.save()

        serializer.save()