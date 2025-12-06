# apps/payments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServicePackageViewSet, TransactionViewSet, VNPayReturnView, VNPayIPNView # <--- Thêm VNPayIPNView


router = DefaultRouter()
router.register(r'packages', ServicePackageViewSet, basename='packages')
router.register(r'transactions', TransactionViewSet, basename='transactions')

urlpatterns = [
    path('', include(router.urls)),
    path('vnpay_return/', VNPayReturnView.as_view(), name='vnpay-return'),
    path('vnpay_ipn/', VNPayIPNView.as_view(), name='vnpay-ipn'), # <--- Thêm dòng này
]