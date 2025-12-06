from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from .models import Resume, WorkExperience, Education, Skill
from .serializers import (
    ResumeSerializer, 
    WorkExperienceSerializer, 
    EducationSerializer, 
    SkillSerializer
)

class ResumeViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # --- TỐI ƯU QUERY ---
        # prefetch_related: Gom tất cả Kinh nghiệm, Học vấn, Kỹ năng trong 1 lần lấy
        # Giúp API load danh sách CV nhanh hơn, tránh lỗi N+1 queries
        return Resume.objects.prefetch_related(
            'experiences', 'educations', 'skills'
        ).filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # Tự động gán CV cho user đang đăng nhập
        serializer.save(user=self.request.user)

    # --- TÍNH NĂNG MỚI: XUẤT PDF CHUẨN HARVARD ---
    @action(detail=True, methods=['get'], url_path='download')
    def download_pdf(self, request, pk=None):
        """
        API xuất CV ra file PDF chuẩn Harvard.
        URL: GET /api/v1/resumes/{id}/download/
        """
        try:
            # Lấy Resume cùng toàn bộ dữ liệu con
            resume = Resume.objects.prefetch_related(
                'educations', 'experiences', 'skills'
            ).get(pk=pk, user=request.user)
        except Resume.DoesNotExist:
            raise NotFound("CV không tồn tại hoặc bạn không có quyền truy cập.")

        # 1. Load template HTML (Bạn cần tạo file html này ở bước trước)
        template_path = 'resumes/harvard_pdf.html'
        template = get_template(template_path)
        
        # 2. Đổ dữ liệu vào template
        context = {'resume': resume}
        html = template.render(context)

        # 3. Tạo file PDF trong bộ nhớ (Response)
        response = HttpResponse(content_type='application/pdf')
        # Đặt tên file tải về (VD: NguyenVanA_CV.pdf)
        filename = f"{resume.full_name.replace(' ', '_')}_CV.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        # 4. Convert HTML -> PDF
        pisa_status = pisa.CreatePDF(
            html, dest=response
        )

        if pisa_status.err:
            return HttpResponse('Có lỗi khi tạo PDF', status=500)
            
        return response

# --- Base Class cho các thành phần con của CV ---
class BaseResumeItemViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Chỉ lấy các item thuộc về CV của user đang login
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