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
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.resumes.models import Resume

class JobViewSet(viewsets.ModelViewSet):
    # Chỉ hiển thị các Job đang PUBLISHED ra ngoài
    queryset = Job.objects.filter(status='PUBLISHED').order_by('-created_at')
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    # --- CẤU HÌNH BỘ LỌC TÌM KIẾM ---
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # 1. Filter chính xác: ?job_type=FULL_TIME&location=Hà Nội
    filterset_fields = ['job_type', 'location', 'company']
    
    # 2. Tìm kiếm theo từ khóa: ?search=Python
    search_fields = ['title', 'description', 'requirements']
    
    # 3. Sắp xếp: ?ordering=-salary_max
    ordering_fields = ['created_at', 'salary_max', 'views_count']

    def perform_create(self, serializer):
        user = self.request.user
        
        # 1. Lấy thông tin company từ dữ liệu người dùng gửi lên
        company = serializer.validated_data.get('company')

        # 2. KIỂM TRA QUYỀN SỞ HỮU CÔNG TY
        # Nếu người đang đăng nhập KHÁC người sở hữu công ty -> Chặn
        if company and company.owner != user:
            raise PermissionDenied("Bạn không có quyền đăng tin cho công ty này vì bạn không phải là chủ sở hữu.")

        # 3. KIỂM TRA & TRỪ LƯỢT ĐĂNG TIN (Chỉ áp dụng cho RECRUITER)
        if user.user_type == 'RECRUITER':
            # a. Kiểm tra ngày hết hạn gói dịch vụ
            # Nếu chưa có ngày hết hạn hoặc ngày đó đã qua
            if not user.membership_expires_at or user.membership_expires_at < timezone.now():
                 raise PermissionDenied("Gói dịch vụ của bạn đã hết hạn hoặc chưa đăng ký. Vui lòng gia hạn để tiếp tục đăng tin.")
            
            # b. Kiểm tra số dư lượt đăng tin
            if user.job_posting_credits <= 0:
                 raise PermissionDenied("Bạn đã hết lượt đăng tin. Vui lòng mua thêm gói dịch vụ.")

            # c. Nếu thỏa mãn -> Trừ đi 1 lượt
            user.job_posting_credits -= 1
            user.save() # Lưu lại số dư mới vào bảng User

        # 4. Lưu Job vào Database
        serializer.save()

    @action(detail=False, methods=['get'], url_path='recommendations')
    def recommendations(self, request):
        """
        API Gợi ý việc làm dựa trên CV chính của ứng viên.
        Logic: Tìm Job có chứa kỹ năng hoặc tiêu đề tương tự CV.
        URL: GET /api/v1/jobs/recommendations/
        """
        user = request.user
        
        # 1. Kiểm tra xem User có phải Candidate không
        if user.user_type != 'CANDIDATE':
            return Response({"detail": "Chỉ dành cho ứng viên."}, status=403)

        # 2. Lấy CV chính của User
        try:
            resume = Resume.objects.get(user=user, is_primary=True)
        except Resume.DoesNotExist:
            # Nếu chưa có CV chính, lấy CV mới nhất
            resume = Resume.objects.filter(user=user).order_by('-created_at').first()
        
        if not resume:
            return Response({"detail": "Bạn cần tạo hồ sơ (CV) trước để nhận gợi ý."}, status=400)

        # 3. Lấy danh sách kỹ năng của ứng viên
        # Giả sử Resume có quan hệ ngược với Skill (related_name='skills')
        user_skills = resume.skills.values_list('name', flat=True) # ['Python', 'Django', 'React']
        
        # 4. Xây dựng truy vấn tìm kiếm (Query)
        # Tìm Job mà Title hoặc Requirements có chứa bất kỳ kỹ năng nào của user
        query = Q()
        
        # Ưu tiên 1: Tiêu đề công việc khớp với tiêu đề CV
        if resume.title:
            query |= Q(title__icontains=resume.title)

        # Ưu tiên 2: Yêu cầu công việc chứa kỹ năng của ứng viên
        for skill in user_skills:
            query |= Q(requirements__icontains=skill) | Q(description__icontains=skill)

        # 5. Lọc và Sắp xếp
        recommended_jobs = Job.objects.filter(
            status='PUBLISHED'
        ).filter(query).distinct().order_by('-created_at')[:10] # Lấy top 10

        # 6. Serialize dữ liệu trả về
        serializer = self.get_serializer(recommended_jobs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='recommendations')
    def recommendations(self, request):
        """
        Gợi ý việc làm dựa trên CV chính của ứng viên.
        """
        user = request.user
        if user.user_type != 'CANDIDATE':
            return Response({"detail": "Chỉ dành cho ứng viên."}, status=403)

        # Lấy CV chính
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

        recommended_jobs = Job.objects.filter(status='PUBLISHED').filter(query).distinct().order_by('-created_at')[:10]

        serializer = self.get_serializer(recommended_jobs, many=True)
        return Response(serializer.data)