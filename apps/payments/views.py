from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from ipware import get_client_ip
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache
import hashlib

from .models import ServicePackage, Transaction
from .serializers import ServicePackageSerializer, TransactionSerializer
from .services import PaymentService, VNPayService

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
        """Tạo giao dịch thanh toán mới với Idempotency-Key support"""
        package_id = request.data.get('package_id')
        
        # CRITICAL FIX #4: DB-based Idempotency (with cache optimization)
        # Client should send unique key per payment attempt (e.g., UUID)
        idempotency_key = request.headers.get('Idempotency-Key')
        
        if idempotency_key:
            # 1. Check cache first (fast path)
            cache_key = f"payment_idempotency:{request.user.id}:{hashlib.sha256(idempotency_key.encode()).hexdigest()}"
            cached_response = cache.get(cache_key)
            if cached_response:
                return Response(cached_response, status=status.HTTP_200_OK)
            
            # 2. Check DB (source of truth - cache có thể mất do Redis restart)
            existing_transaction = Transaction.objects.filter(
                user=request.user,
                idempotency_key=idempotency_key
            ).first()
            
            if existing_transaction:
                # Return existing transaction (idempotent response)
                response_data = {
                    "payment_url": VNPayService.generate_payment_url(
                        package=existing_transaction.package,
                        trans_code=existing_transaction.transaction_code,
                        client_ip=get_client_ip(request)[0] or '127.0.0.1'
                    ),
                    "transaction_code": existing_transaction.transaction_code
                }
                # Re-cache for future requests
                cache.set(cache_key, response_data, timeout=60 * 60 * 24)
                return Response(response_data, status=status.HTTP_200_OK)
        
        try:
            # Lấy IP với django-ipware (chống spoofing)
            client_ip, is_routable = get_client_ip(request)
            
            # Sử dụng Service Layer để tạo payment (với idempotency_key)
            result = PaymentService.create_payment_transaction(
                user=request.user,
                package_id=package_id,
                idempotency_key=idempotency_key  # Pass to service
            )
            
            # Regenerate payment URL với IP thực của client
            result['payment_url'] = VNPayService.generate_payment_url(
                package=result['transaction'].package,
                trans_code=result['transaction_code'],
                client_ip=client_ip or '127.0.0.1'
            )
            
            response_data = {
                "payment_url": result['payment_url'],
                "transaction_code": result['transaction_code']
            }
            
            # Cache successful response for 24 hours if Idempotency-Key provided
            if idempotency_key:
                cache.set(cache_key, response_data, timeout=60 * 60 * 24)  # 24 hours
            
            return Response(response_data)
            
        except ServicePackage.DoesNotExist:
            return Response(
                {"error": _("Package does not exist")}, 
                status=status.HTTP_404_NOT_FOUND
            )

class VNPayBaseView(APIView):
    """Base class xử lý callback từ VNPay (ReturnURL và IPN)"""
    
    def process_payment(self, request):
        """
        Xử lý callback từ VNPay
        
        Returns:
            tuple: (transaction, message, is_success)
        """
        input_data = request.GET.dict()
        if not input_data:
            return None, _("No data"), False
        
        # Validate checksum
        if not VNPayService.validate_callback(input_data):
            return None, _("Invalid Checksum"), False
        
        # Extract thông tin từ callback
        transaction_code = input_data.get('vnp_TxnRef')
        amount = int(input_data.get('vnp_Amount')) / 100
        response_code = input_data.get('vnp_ResponseCode')
        
        # Gọi Service Layer để xử lý
        return PaymentService.process_payment_callback(
            transaction_code=transaction_code,
            amount=amount,
            response_code=response_code
        )

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