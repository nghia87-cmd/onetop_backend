# apps/core/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from apps.jobs.models import Job
from apps.core.websocket_ticket import WebSocketTicketService


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