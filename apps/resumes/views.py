import logging
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from .models import Resume, WorkExperience, Education, Skill
from .serializers import (
    ResumeSerializer, 
    WorkExperienceSerializer, 
    EducationSerializer, 
    SkillSerializer
)

# Import task Celery đã tạo (file apps/resumes/tasks.py)
from .tasks import generate_resume_pdf_async

# Import throttling
from apps.core.throttling import PDFGenerationThrottle

logger = logging.getLogger(__name__)

class ResumeViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # --- TỐI ƯU QUERY ---
        # prefetch_related: Gom tất cả Kinh nghiệm, Học vấn, Kỹ năng trong 1 lần lấy
        return Resume.objects.prefetch_related(
            'experiences', 'educations', 'skills'
        ).filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # Tự động gán CV cho user đang đăng nhập
        serializer.save(user=self.request.user)

    # ==================================================================
    # [NÂNG CẤP] XUẤT PDF BẤT ĐỒNG BỘ (ASYNC) - KHẮC PHỤC TREO SERVER
    # [BẢO MẬT] Thêm throttling để tránh spam
    # ==================================================================
    
    @action(detail=True, methods=['post'], url_path='generate-pdf', 
            throttle_classes=[PDFGenerationThrottle])
    def generate_pdf(self, request, pk=None):
        """
        API Trigger việc tạo PDF qua Celery Worker (Non-blocking).
        Giới hạn: 5 requests/hour per user để tránh spam
        Frontend gọi API này, nhận về 'PROCESSING', sau đó đợi thông báo hoặc poll API download.
        URL: POST /api/v1/resumes/{id}/generate-pdf/
        """
        # Kiểm tra quyền sở hữu
        try:
            resume = Resume.objects.get(pk=pk, user=request.user)
        except Resume.DoesNotExist:
            raise NotFound("CV không tồn tại hoặc bạn không có quyền truy cập.")
        
        # (Tuỳ chọn) Kiểm tra nếu file đã có rồi thì báo luôn
        if resume.pdf_file and resume.pdf_file.storage.exists(resume.pdf_file.name):
             return Response(
                {
                    "status": "READY", 
                    "message": "File PDF đã sẵn sàng.",
                    "download_url": resume.pdf_file.url
                },
                status=status.HTTP_200_OK
            )
        
        # Kích hoạt Celery Task (Task trả về ngay lập tức, worker sẽ xử lý sau)
        task = generate_resume_pdf_async.delay(resume.id)
        
        logger.info(f"PDF generation task started for resume {pk}. Task ID: {task.id}")
        
        return Response(
            {
                "message": "Yêu cầu tạo PDF đã được tiếp nhận. Bạn sẽ nhận được thông báo khi hoàn tất.",
                "status": "PROCESSING",
                "task_id": task.id,
            },
            status=status.HTTP_202_ACCEPTED
        )

    @action(detail=True, methods=['get'], url_path='download')
    def download_pdf(self, request, pk=None):
        """
        API tải file PDF đã được tạo (Chỉ trả về URL file tĩnh).
        URL: GET /api/v1/resumes/{id}/download/
        """
        try:
            resume = Resume.objects.get(pk=pk, user=request.user)
        except Resume.DoesNotExist:
            raise NotFound("CV không tồn tại hoặc bạn không có quyền truy cập.")

        # Kiểm tra xem task Celery đã tạo xong file và lưu vào DB chưa
        if not resume.pdf_file:
            return Response(
                {
                    "status": "PENDING", 
                    "detail": "File PDF chưa được tạo hoặc đang xử lý. Vui lòng gọi API /generate-pdf/ trước."
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Trả về URL file để Frontend tải xuống
        return Response(
            {
                "status": "READY", 
                "download_url": resume.pdf_file.url
            },
            status=status.HTTP_200_OK
        )

# --- Base Class cho các thành phần con của CV (GIỮ NGUYÊN) ---
class BaseResumeItemViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Chỉ lấy các item thuộc về CV của user đang login
        if not hasattr(self, 'queryset_model'):
            return []
        return self.queryset_model.objects.filter(resume__user=self.request.user)

    def perform_create(self, serializer):
        # Kiểm tra xem resume_id gửi lên có thuộc về user này không
        resume_id = self.request.data.get('resume')
        try:
            resume = Resume.objects.get(id=resume_id, user=self.request.user)
            serializer.save(resume=resume)
        except Resume.DoesNotExist:
            raise NotFound("Không tìm thấy CV hoặc bạn không có quyền sửa CV này.")

class WorkExperienceViewSet(BaseResumeItemViewSet):
    queryset_model = WorkExperience
    queryset = WorkExperience.objects.all()
    serializer_class = WorkExperienceSerializer

class EducationViewSet(BaseResumeItemViewSet):
    queryset_model = Education
    queryset = Education.objects.all()
    serializer_class = EducationSerializer

class SkillViewSet(BaseResumeItemViewSet):
    queryset_model = Skill
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer