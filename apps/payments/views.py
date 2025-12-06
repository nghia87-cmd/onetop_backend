from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone
from django.db import transaction as db_transaction # Đổi tên để tránh trùng với model Transaction
import datetime
import uuid
from datetime import timedelta 

from .models import ServicePackage, Transaction
from .serializers import ServicePackageSerializer, TransactionSerializer
from .vnpay import vnpay

class ServicePackageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServicePackage.objects.all()
    serializer_class = ServicePackageSerializer
    permission_classes = [permissions.AllowAny]

class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'])
    def create_payment(self, request):
        package_id = request.data.get('package_id')
        try:
            package = ServicePackage.objects.get(id=package_id)
        except ServicePackage.DoesNotExist:
            return Response({"error": "Gói không tồn tại"}, status=status.HTTP_404_NOT_FOUND)

        order_id = int(timezone.now().timestamp())
        trans_code = str(order_id)

        # Tạo giao dịch PENDING
        transaction = Transaction.objects.create(
            user=request.user,
            package=package,
            amount=package.price,
            transaction_code=trans_code,
            status='PENDING'
        )

        # Tạo URL thanh toán VNPay
        vnp = vnpay()
        vnp.requestData['vnp_Version'] = '2.1.0'
        vnp.requestData['vnp_Command'] = 'pay'
        vnp.requestData['vnp_TmnCode'] = settings.VNPAY_TMN_CODE
        vnp.requestData['vnp_Amount'] = int(package.price * 100)
        vnp.requestData['vnp_CurrCode'] = 'VND'
        vnp.requestData['vnp_TxnRef'] = trans_code
        vnp.requestData['vnp_OrderInfo'] = f"Thanh toan don hang {trans_code}"
        vnp.requestData['vnp_OrderType'] = 'billpayment'
        vnp.requestData['vnp_Locale'] = 'vn'
        
        ipaddr = self.get_client_ip(request)
        vnp.requestData['vnp_IpAddr'] = ipaddr
        
        vnp.requestData['vnp_CreateDate'] = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        vnp.requestData['vnp_ReturnUrl'] = settings.VNPAY_RETURN_URL
        
        vnpay_payment_url = vnp.get_payment_url(settings.VNPAY_URL, settings.VNPAY_HASH_SECRET)

        return Response({
            "payment_url": vnpay_payment_url,
            "transaction_code": trans_code
        })

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class VNPayBaseView(APIView):
    """Class cha chứa logic xử lý chung cho cả ReturnURL và IPN"""
    
    def process_payment(self, request):
        inputData = request.GET.dict()
        if not inputData:
            return None, "No data", False

        vnp = vnpay()
        vnp.responseData = inputData
        order_id = inputData.get('vnp_TxnRef')
        amount = int(inputData.get('vnp_Amount')) / 100
        vnp_ResponseCode = inputData.get('vnp_ResponseCode')

        if vnp.validate_response(settings.VNPAY_HASH_SECRET):
            # BẮT ĐẦU TRANSACTION DATABASE (Khóa bản ghi để tránh xử lý trùng lặp)
            with db_transaction.atomic():
                try:
                    trans = Transaction.objects.select_for_update().get(transaction_code=order_id)
                except Transaction.DoesNotExist:
                    return None, "Order not found", False

                if trans.amount != amount:
                    return None, "Invalid amount", False

                if trans.status != 'PENDING':
                    return trans, "Order already confirmed", True

                if vnp_ResponseCode == "00":
                    # --- THANH TOÁN THÀNH CÔNG ---
                    trans.status = 'SUCCESS'
                    trans.save()
                    
                    user = trans.user
                    package = trans.package
                    
                    if package:
                        # 1. Cộng ngày hết hạn (Chung cho cả Credit và Subscription)
                        now = timezone.now()
                        if user.membership_expires_at and user.membership_expires_at > now:
                            user.membership_expires_at += timedelta(days=package.duration_days)
                        else:
                            user.membership_expires_at = now + timedelta(days=package.duration_days)
                        
                        # 2. Kích hoạt quyền lợi dựa trên loại gói
                        if package.package_type == 'SUBSCRIPTION':
                            # Gói thuê bao: Bật cờ VIP
                            if package.allow_unlimited_posting:
                                user.has_unlimited_posting = True
                            if package.allow_view_contact:
                                user.can_view_contact = True
                        else:
                            # Gói Credit: Cộng số lượt đăng tin
                            user.job_posting_credits += package.job_posting_limit
                        
                        user.save()
                    
                    return trans, "Confirm Success", True
                else:
                    # --- THANH TOÁN THẤT BẠI ---
                    trans.status = 'FAILED'
                    trans.save()
                    return trans, "Payment Failed", False
        else:
            return None, "Invalid Checksum", False

class VNPayReturnView(VNPayBaseView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        trans, message, is_success = self.process_payment(request)
        
        if not trans:
            return Response({"RspCode": "99", "Message": message}, status=status.HTTP_400_BAD_REQUEST)
        
        if is_success:
            return Response({
                "RspCode": "00", 
                "Message": message, 
                "data": {
                    "credits": trans.user.job_posting_credits,
                    "expires_at": trans.user.membership_expires_at,
                    "is_vip": trans.user.has_unlimited_posting # Trả về thêm cờ VIP để frontend biết
                }
            })
        else:
            return Response({"RspCode": "00", "Message": message, "status": "FAILED"})

class VNPayIPNView(VNPayBaseView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        trans, message, is_success = self.process_payment(request)
        
        if not trans:
            return Response({"RspCode": "01", "Message": message}, status=status.HTTP_200_OK)
        
        return Response({"RspCode": "00", "Message": message}, status=status.HTTP_200_OK)