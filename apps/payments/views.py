from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone
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

        transaction = Transaction.objects.create(
            user=request.user,
            package=package,
            amount=package.price,
            transaction_code=trans_code,
            status='PENDING'
        )

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

class VNPayReturnView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        inputData = request.GET.dict()
        if not inputData:
            return Response({"error": "No data"}, status=status.HTTP_400_BAD_REQUEST)

        vnp = vnpay()
        vnp.responseData = inputData
        order_id = inputData.get('vnp_TxnRef')
        amount = int(inputData.get('vnp_Amount')) / 100
        vnp_ResponseCode = inputData.get('vnp_ResponseCode')
        
        if vnp.validate_response(settings.VNPAY_HASH_SECRET):
            try:
                transaction = Transaction.objects.get(transaction_code=order_id)
            except Transaction.DoesNotExist:
                return Response({"RspCode": "01", "Message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

            if transaction.amount != amount:
                return Response({"RspCode": "04", "Message": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

            if transaction.status != 'PENDING':
                return Response({"RspCode": "02", "Message": "Order already confirmed"}, status=status.HTTP_200_OK)

            if vnp_ResponseCode == "00":
                transaction.status = 'SUCCESS'
                transaction.save()
                
                user = transaction.user
                package = transaction.package
                
                if package:
                    user.job_posting_credits += package.job_posting_limit
                    now = timezone.now()
                    if user.membership_expires_at and user.membership_expires_at > now:
                        user.membership_expires_at += timedelta(days=package.duration_days)
                    else:
                        user.membership_expires_at = now + timedelta(days=package.duration_days)
                    user.save()

                return Response({
                    "RspCode": "00", 
                    "Message": "Confirm Success", 
                    "data": {
                        "credits": user.job_posting_credits,
                        "expires_at": user.membership_expires_at
                    }
                })
            else:
                transaction.status = 'FAILED'
                transaction.save()
                return Response({"RspCode": "00", "Message": "Payment Failed", "status": "FAILED"})
        else:
            return Response({"RspCode": "97", "Message": "Invalid Checksum"}, status=status.HTTP_400_BAD_REQUEST)