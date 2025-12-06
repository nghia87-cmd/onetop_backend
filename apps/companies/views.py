from rest_framework import viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from .models import Company
from .serializers import CompanySerializer
from apps.jobs.models import Job
from apps.applications.models import Application

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all().order_by('-created_at')
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        if self.request.user.user_type != 'RECRUITER':
            raise PermissionDenied("Chỉ Nhà tuyển dụng mới được tạo công ty.")
        serializer.save(owner=self.request.user)
    
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """
        Dashboard thống kê cho Nhà tuyển dụng.
        """
        user = request.user
        if user.user_type != 'RECRUITER':
            return Response({"detail": "Chỉ dành cho nhà tuyển dụng."}, status=403)

        my_jobs = Job.objects.filter(company__owner=user)
        
        total_jobs = my_jobs.count()
        active_jobs = my_jobs.filter(status='PUBLISHED').count()
        total_views = my_jobs.aggregate(Sum('views_count'))['views_count__sum'] or 0
        
        total_applications = Application.objects.filter(job__in=my_jobs).count()
        new_applications = Application.objects.filter(job__in=my_jobs, status='PENDING').count()

        return Response({
            "overview": {
                "total_jobs": total_jobs,
                "active_jobs": active_jobs,
                "total_views": total_views,
                "credits_left": user.job_posting_credits,
                "vip_expiry": user.membership_expires_at
            },
            "applications": {
                "total": total_applications,
                "new": new_applications
            }
        })