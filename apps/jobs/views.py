from rest_framework import viewsets, permissions, filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
# Import Q từ elasticsearch_dsl và đổi tên để tránh nhầm với Django Q
from elasticsearch_dsl import Q as ES_Q

from .models import Job, SavedJob
from .serializers import JobSerializer, SavedJobSerializer
# Import Document Elasticsearch đã định nghĩa
from .documents import JobDocument
from apps.resumes.models import Resume
from .services import JobService  # Import Service Layer

# ====================================================================
# JOB VIEWSET (ELASTICSEARCH INTEGRATED)
# ====================================================================
class JobViewSet(viewsets.ModelViewSet):
    # Queryset gốc vẫn dùng DB cho các tác vụ CRUD cơ bản
    queryset = Job.objects.select_related('company').filter(status='PUBLISHED').order_by('-created_at')
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    # Filter của DRF chỉ áp dụng khi không search hoặc search trên DB
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['job_type', 'location']
    ordering_fields = ['created_at', 'salary_max', 'views_count']

    def list(self, request, *args, **kwargs):
        """
        Override hàm list để chuyển hướng tìm kiếm sang Elasticsearch
        khi có tham số ?search=...
        """
        search_term = request.query_params.get('search', '')
        
        # 1. Nếu KHÔNG có từ khóa -> Dùng logic mặc định của Django (DB)
        if not search_term:
            return super().list(request, *args, **kwargs)

        # 2. Nếu CÓ từ khóa -> Dùng Elasticsearch
        # Tìm kiếm trên nhiều trường, ưu tiên Title (nhân 3 điểm)
        q = ES_Q("multi_match", query=search_term, fields=[
            'title^3',          # Title khớp: x3 điểm
            'requirements', 
            'description', 
            'company.name'
        ], fuzziness='AUTO')    # Chấp nhận lỗi chính tả nhẹ

        # Filter: Chỉ tìm Job đang PUBLISHED
        search = JobDocument.search().query(q).filter('term', status='PUBLISHED')

        # Convert kết quả ES về Django QuerySet (giữ nguyên thứ tự Rank)
        qs = search.to_queryset()

        # Phân trang kết quả
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        """
        Refactored: Sử dụng JobService thay vì xử lý logic trong View
        
        View chỉ làm nhiệm vụ nhận request và gọi Service Layer
        """
        JobService.create_job(
            user=self.request.user,
            validated_data=serializer.validated_data
        )

    @action(detail=False, methods=['get'], url_path='recommendations')
    def recommendations(self, request):
        """
        Gợi ý việc làm thông minh sử dụng Elasticsearch Bool Query
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

        # --- ELASTICSEARCH RECOMMENDATION LOGIC ---
        should_conditions = []
        
        # 1. Matching Tiêu đề CV (Boost 2.0 - Quan trọng)
        # Nếu CV là "Python Developer", ưu tiên Job có title chứa từ này
        if resume.title:
            should_conditions.append(
                ES_Q('match', title={'query': resume.title, 'boost': 2.0})
            )
        
        # 2. Matching Kỹ năng (Boost 1.0 - Bình thường)
        # Tìm các skill của ứng viên trong phần Yêu cầu & Mô tả của Job
        user_skills = list(resume.skills.values_list('name', flat=True))
        for skill in user_skills:
            should_conditions.append(ES_Q('match', requirements=skill))
            should_conditions.append(ES_Q('match', description=skill))

        # 3. Tạo Bool Query: "SHOULD" 
        # Càng thỏa mãn nhiều điều kiện skill/title thì điểm (score) càng cao
        q = ES_Q('bool', should=should_conditions, minimum_should_match=1)

        # 4. Execute Search
        search = JobDocument.search().query(q).filter('term', status='PUBLISHED')
        
        # Lấy 10 kết quả tốt nhất (ES tự động sort theo _score giảm dần)
        qs = search.to_queryset()[:10]

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

# ====================================================================
# SAVED JOB VIEWSET
# ====================================================================
class SavedJobViewSet(viewsets.ModelViewSet):
    """
    API Quản lý việc làm đã lưu (Bookmarks) - Giữ nguyên dùng DB
    """
    serializer_class = SavedJobSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedJob.objects.filter(user=self.request.user).select_related('job', 'job__company').order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)