# apps/core/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from apps.jobs.models import Job

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