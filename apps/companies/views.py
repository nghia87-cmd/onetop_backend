from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied # <--- Thêm cái này để báo lỗi chặn quyền
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from .models import Company
from .serializers import CompanySerializer
from apps.jobs.models import Job
from apps.applications.models import Application

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Chỉ cho phép chủ sở hữu (Owner) được sửa/xóa công ty của mình.
    Người khác chỉ được xem (Read Only).
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all().order_by('-created_at')
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        # --- FIX LỖI BẢO MẬT ---
        # Chỉ cho phép Nhà tuyển dụng (RECRUITER) tạo công ty.
        # Nếu là Ứng viên (CANDIDATE) thì chặn lại ngay.
        if self.request.user.user_type != 'RECRUITER':
            raise PermissionDenied("Bạn không có quyền tạo công ty. Tài khoản phải là Nhà tuyển dụng.")
            
        # Tự động gán người tạo là User đang login
        serializer.save(owner=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """
        API Thống kê cho Nhà tuyển dụng (Recruiter dashboard).
        URL: GET /api/v1/companies/stats/
        """
        user = request.user
        
        # Kiểm tra quyền: Chỉ NTD mới xem được thống kê
        if user.user_type != 'RECRUITER':
            return Response({"detail": "Chỉ dành cho nhà tuyển dụng."}, status=403)

        # 1. Lấy tất cả job của user này
        my_jobs = Job.objects.filter(company__owner=user)
        
        # 2. Tính toán số liệu
        total_jobs = my_jobs.count()
        active_jobs = my_jobs.filter(status='PUBLISHED').count()
        total_views = my_jobs.aggregate(Sum('views_count'))['views_count__sum'] or 0
        
        # 3. Đếm số lượng đơn ứng tuyển (Applications)
        total_applications = Application.objects.filter(job__in=my_jobs).count()
        
        # 4. Đếm đơn mới (Pending)
        new_applications = Application.objects.filter(job__in=my_jobs, status='PENDING').count()

        return Response({
            "overview": {
                "total_jobs": total_jobs,
                "active_jobs": active_jobs,
                "total_views": total_views,
                "credits_left": user.job_posting_credits, # Số lượt đăng tin còn lại
                "vip_expiry": user.membership_expires_at  # Ngày hết hạn VIP
            },
            "applications": {
                "total": total_applications,
                "new": new_applications
            }
        })