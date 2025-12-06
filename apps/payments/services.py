"""
Payment Service Layer
Tách biệt Business Logic khỏi Views để dễ test và tái sử dụng
"""
from django.conf import settings
from django.utils import timezone
from django.db import transaction as db_transaction
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
import datetime
import logging

from .models import ServicePackage, Transaction
from .vnpay import vnpay

logger = logging.getLogger(__name__)


class PaymentService:
    """Service xử lý logic thanh toán và membership"""
    
    @staticmethod
    def create_payment_transaction(user, package_id):
        """
        Tạo transaction PENDING và URL thanh toán VNPay
        
        Args:
            user: User object
            package_id: ID của ServicePackage
            
        Returns:
            dict: {
                'payment_url': str,
                'transaction_code': str,
                'transaction': Transaction object
            }
            
        Raises:
            ServicePackage.DoesNotExist: Nếu gói không tồn tại
        """
        package = ServicePackage.objects.get(id=package_id)
        
        # Tạo mã giao dịch unique
        order_id = int(timezone.now().timestamp())
        trans_code = str(order_id)
        
        # Tạo transaction PENDING
        transaction = Transaction.objects.create(
            user=user,
            package=package,
            amount=package.price,
            transaction_code=trans_code,
            status='PENDING'
        )
        
        logger.info(f"Created transaction {trans_code} for user {user.id}, package {package.name}")
        
        return {
            'payment_url': VNPayService.generate_payment_url(package, trans_code),
            'transaction_code': trans_code,
            'transaction': transaction
        }
    
    @staticmethod
    def process_payment_callback(transaction_code, amount, response_code, validate_checksum=True):
        """
        Xử lý callback từ VNPay (dùng cho cả ReturnURL và IPN)
        
        Args:
            transaction_code: Mã giao dịch
            amount: Số tiền (đã chia 100)
            response_code: Mã phản hồi từ VNPay
            validate_checksum: Có validate chữ ký không (default True)
            
        Returns:
            tuple: (transaction, message, is_success)
        """
        # BẮT ĐẦU TRANSACTION DATABASE (Khóa bản ghi để tránh xử lý trùng lặp)
        with db_transaction.atomic():
            try:
                trans = Transaction.objects.select_for_update().get(transaction_code=transaction_code)
            except Transaction.DoesNotExist:
                logger.error(f"Transaction {transaction_code} not found")
                return None, _("Order not found"), False
            
            # Kiểm tra số tiền
            if trans.amount != amount:
                logger.error(f"Amount mismatch for {transaction_code}: expected {trans.amount}, got {amount}")
                return None, _("Invalid amount"), False
            
            # Nếu đã xử lý rồi, trả về kết quả (Idempotent)
            if trans.status != 'PENDING':
                logger.info(f"Transaction {transaction_code} already processed with status {trans.status}")
                return trans, _("Order already confirmed"), True
            
            # Xử lý theo response code
            if response_code == "00":
                # THANH TOÁN THÀNH CÔNG
                trans.status = 'SUCCESS'
                trans.save()
                
                # Cập nhật membership cho user
                PaymentService._activate_membership(trans.user, trans.package)
                
                logger.info(f"Transaction {transaction_code} SUCCESS - Membership activated for user {trans.user.id}")
                return trans, _("Confirm Success"), True
            else:
                # THANH TOÁN THẤT BẠI
                trans.status = 'FAILED'
                trans.save()
                
                logger.warning(f"Transaction {transaction_code} FAILED with code {response_code}")
                return trans, _("Payment Failed"), False
    
    @staticmethod
    def _activate_membership(user, package):
        """
        Kích hoạt quyền lợi membership cho user
        
        Logic phức tạp này đã được tách ra để dễ test và maintain
        """
        if not package:
            return
        
        now = timezone.now()
        
        # 1. Cộng ngày hết hạn (Chung cho cả Credit và Subscription)
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
        logger.info(f"Membership activated for user {user.id}: credits={user.job_posting_credits}, expires={user.membership_expires_at}")


class VNPayService:
    """Service xử lý tích hợp VNPay"""
    
    @staticmethod
    def generate_payment_url(package, trans_code, client_ip='127.0.0.1'):
        """
        Tạo URL thanh toán VNPay
        
        Args:
            package: ServicePackage object
            trans_code: Mã giao dịch
            client_ip: IP của client (default 127.0.0.1)
            
        Returns:
            str: URL thanh toán VNPay
        """
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
        vnp.requestData['vnp_IpAddr'] = client_ip
        vnp.requestData['vnp_CreateDate'] = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        vnp.requestData['vnp_ReturnUrl'] = settings.VNPAY_RETURN_URL
        
        payment_url = vnp.get_payment_url(settings.VNPAY_URL, settings.VNPAY_HASH_SECRET)
        
        logger.debug(f"Generated VNPay URL for transaction {trans_code}")
        return payment_url
    
    @staticmethod
    def validate_callback(request_data):
        """
        Validate checksum từ VNPay callback
        
        Args:
            request_data: dict chứa tất cả params từ VNPay
            
        Returns:
            bool: True nếu checksum hợp lệ
        """
        vnp = vnpay()
        vnp.responseData = request_data
        is_valid = vnp.validate_response(settings.VNPAY_HASH_SECRET)
        
        if not is_valid:
            logger.error(f"Invalid VNPay checksum for txnRef {request_data.get('vnp_TxnRef')}")
        
        return is_valid
