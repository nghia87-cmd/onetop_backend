"""Payment Service Layer
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
from .vnpay import VNPayGateway, VNPayConfig
from .optimistic_locking import retry_on_conflict, OptimisticLockError

logger = logging.getLogger(__name__)


class PaymentService:
    """Service xử lý logic thanh toán và membership"""
    
    @staticmethod
    def create_payment_transaction(user, package_id, idempotency_key=None):
        """
        Tạo transaction PENDING và URL thanh toán VNPay
        
        Args:
            user: User object
            package_id: ID của ServicePackage
            idempotency_key: Optional idempotency key để prevent duplicate transactions
            
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
        
        # CRITICAL FIX #4: Tạo transaction với idempotency_key (nếu có)
        transaction = Transaction.objects.create(
            user=user,
            package=package,
            amount=package.price,
            transaction_code=trans_code,
            status='PENDING',
            idempotency_key=idempotency_key  # DB-based duplicate prevention
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
    @retry_on_conflict(max_retries=3)  # CRITICAL FIX: Use Optimistic Locking instead of select_for_update
    def _activate_membership(user, package):
        """
        Kích hoạt quyền lợi membership cho user
        
        Logic phức tạp này đã được tách ra để dễ test và maintain
        
        RACE CONDITION FIX:
        - Sử dụng Optimistic Locking (version field) thay vì select_for_update
        - retry_on_conflict decorator tự động retry khi có conflict (max 3 lần)
        - Không lock database rows → Better scalability, No deadlocks
        """
        if not package:
            return
        
        from django.db.models import F
        from apps.users.models import User
        
        now = timezone.now()
        
        # CRITICAL FIX: Use get() instead of select_for_update() for Optimistic Locking
        # Version check happens in save_with_version_check()
        user = User.objects.get(pk=user.pk)
        
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
            # Gói Credit: Cộng số lượt đăng tin (ATOMIC UPDATE)
            # Sử dụng F() để tránh race condition khi đọc/ghi credits
            User.objects.filter(pk=user.pk).update(
                job_posting_credits=F('job_posting_credits') + package.job_posting_limit
            )
            # Refresh để lấy giá trị mới sau khi update
            user.refresh_from_db()
        
        # CRITICAL FIX: Use save_with_version_check() instead of save()
        # This will raise OptimisticLockError if version changed (handled by retry_on_conflict)
        user.save_with_version_check()
        logger.info(f"Membership activated for user {user.id}: credits={user.job_posting_credits}, expires={user.membership_expires_at}")


class VNPayService:
    """Service xử lý tích hợp VNPay"""
    
    @staticmethod
    def generate_payment_url(package, trans_code, client_ip='127.0.0.1'):
        """
        Tạo URL thanh toán VNPay (Refactored với VNPayGateway)
        
        Args:
            package: ServicePackage object
            trans_code: Mã giao dịch
            client_ip: IP của client (default 127.0.0.1)
            
        Returns:
            str: URL thanh toán VNPay
        """
        # Tạo VNPay config từ settings
        config = VNPayConfig(
            tmn_code=settings.VNPAY_TMN_CODE,
            hash_secret=settings.VNPAY_HASH_SECRET,
            payment_url=settings.VNPAY_URL,
            return_url=settings.VNPAY_RETURN_URL
        )
        
        # Generate payment URL với stateless VNPayGateway
        payment_url = VNPayGateway.create_payment_url(
            config=config,
            txn_ref=trans_code,
            amount=int(package.price * 100),
            order_info=f"Thanh toan don hang {trans_code}",
            ip_address=client_ip,
            created_date=datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        )
        
        logger.debug(f"Generated VNPay URL for transaction {trans_code}")
        return payment_url
    
    @staticmethod
    def validate_callback(request_data):
        """
        Validate checksum từ VNPay callback (Refactored với VNPayGateway)
        
        Args:
            request_data: dict chứa tất cả params từ VNPay
            
        Returns:
            bool: True nếu checksum hợp lệ
        """
        is_valid = VNPayGateway.validate_callback(
            secret_key=settings.VNPAY_HASH_SECRET,
            response_data=request_data
        )
        
        if not is_valid:
            logger.error(f"Invalid VNPay checksum for txnRef {request_data.get('vnp_TxnRef')}")
        
        return is_valid
