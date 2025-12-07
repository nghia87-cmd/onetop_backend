# apps/core/views.py
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
import os

from apps.jobs.models import Job
from apps.core.websocket_ticket import WebSocketTicketService
from apps.resumes.models import Resume
from apps.applications.models import Application


class WebSocketTicketView(APIView):
    """
    API endpoint để lấy one-time ticket cho WebSocket
    
    POST /api/v1/ws-ticket/
    Headers: Authorization: Bearer <access_token>
    
    Response:
    {
        "ticket": "random_32_char_string",
        "expires_in": 10
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Generate ticket cho user hiện tại"""
        user = request.user
        ticket = WebSocketTicketService.generate_ticket(user.id)
        
        return Response({
            "ticket": ticket,
            "expires_in": WebSocketTicketService.TICKET_EXPIRY,
            "message": "Use this ticket to connect WebSocket within 10 seconds"
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_resume_pdf(request, resume_id):
    """
    Secure download for Resume PDF files
    Only allows:
    - Resume owner
    - Recruiters who received applications from this user
    """
    resume = get_object_or_404(Resume, id=resume_id)
    
    # Permission check
    if request.user == resume.user:
        pass  # Owner can download
    elif request.user.user_type == 'RECRUITER':
        # Recruiter can only download if they received application from this user
        has_application = Application.objects.filter(
            candidate=resume.user,
            job__company__owner=request.user
        ).exists()
        if not has_application:
            return Response(
                {"detail": "You don't have permission to access this resume."},
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        return Response(
            {"detail": "You don't have permission to access this resume."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get file path
    if not resume.pdf_file:
        raise Http404("PDF file not found")
    
    file_path = resume.pdf_file.path
    if not os.path.exists(file_path):
        raise Http404("File does not exist on server")
    
    # Use X-Accel-Redirect for Nginx (production)
    response = HttpResponse()
    response['X-Accel-Redirect'] = f'/protected/resumes/pdf/{os.path.basename(resume.pdf_file.name)}'
    response['Content-Type'] = 'application/pdf'
    response['Content-Disposition'] = f'attachment; filename="{resume.user.full_name}_CV.pdf"'
    
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_application_cv(request, application_id):
    """
    Secure download for Application CV files
    Only allows:
    - Application candidate (owner)
    - Job recruiter (company owner)
    """
    application = get_object_or_404(Application, id=application_id)
    
    # Permission check
    if request.user == application.candidate:
        pass  # Candidate can download their own CV
    elif request.user.user_type == 'RECRUITER':
        if application.job.company.owner != request.user:
            return Response(
                {"detail": "You don't have permission to access this application."},
                status=status.HTTP_403_FORBIDDEN
            )
    else:
        return Response(
            {"detail": "You don't have permission to access this application."},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get file path
    if not application.cv_file:
        raise Http404("CV file not found")
    
    file_path = application.cv_file.path
    if not os.path.exists(file_path):
        raise Http404("File does not exist on server")
    
    # Use X-Accel-Redirect for Nginx
    response = HttpResponse()
    response['X-Accel-Redirect'] = f'/protected/applications/cv/{os.path.basename(application.cv_file.name)}'
    response['Content-Type'] = 'application/pdf'
    response['Content-Disposition'] = f'attachment; filename="{application.candidate.full_name}_Application.pdf"'
    
    return response


class GeneralConfigView(APIView):
    """
    API trả về các cấu hình chung, danh sách lựa chọn (Choices)
    để Frontend hiển thị Dropdown/Filter.
    URL: GET /api/v1/config/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "job_types": [
                {"value": k, "label": v} for k, v in Job.JobType.choices
            ],
            "job_statuses": [
                {"value": k, "label": v} for k, v in Job.Status.choices
            ],
            # Bạn có thể thêm danh sách tỉnh thành ở đây nếu có model Location
            "locations": [
                "Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Cần Thơ", "Remote"
            ]
        })