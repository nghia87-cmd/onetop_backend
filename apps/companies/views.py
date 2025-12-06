from rest_framework import viewsets, permissions
from .models import Company
from .serializers import CompanySerializer

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
        serializer.save(owner=self.request.user)