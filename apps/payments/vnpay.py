"""
VNPay Payment Gateway Integration
Refactored to be Pythonic with stateless design and type hints
"""
import hashlib
import hmac
import urllib.parse
from typing import Dict, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class VNPayConfig:
    """VNPay configuration container"""
    tmn_code: str
    hash_secret: str
    payment_url: str
    return_url: str
    version: str = '2.1.0'
    command: str = 'pay'
    currency: str = 'VND'
    locale: str = 'vn'


class VNPayGateway:
    """
    VNPay Payment Gateway (Pythonic Refactored Version)
    
    Design principles:
    - Stateless: Không dùng instance variables để lưu request/response data
    - Pure functions: Methods nhận input, trả output, không side effects
    - Type hints: Rõ ràng về kiểu dữ liệu input/output
    """
    
    @staticmethod
    def create_payment_url(
        config: VNPayConfig,
        txn_ref: str,
        amount: int,
        order_info: str,
        ip_address: str,
        created_date: str
    ) -> str:
        """
        Tạo URL thanh toán VNPay
        
        Args:
            config: VNPay configuration
            txn_ref: Mã giao dịch (unique)
            amount: Số tiền (VND, đã nhân 100)
            order_info: Mô tả đơn hàng
            ip_address: IP của client
            created_date: Thời gian tạo (format: YYYYMMDDHHmmss)
            
        Returns:
            str: Full payment URL với signature
        """
        # Build request data
        request_data = {
            'vnp_Version': config.version,
            'vnp_Command': config.command,
            'vnp_TmnCode': config.tmn_code,
            'vnp_Amount': str(amount),
            'vnp_CurrCode': config.currency,
            'vnp_TxnRef': txn_ref,
            'vnp_OrderInfo': order_info,
            'vnp_OrderType': 'billpayment',
            'vnp_Locale': config.locale,
            'vnp_IpAddr': ip_address,
            'vnp_CreateDate': created_date,
            'vnp_ReturnUrl': config.return_url,
        }
        
        # Generate signature và build URL
        query_string = VNPayGateway._build_query_string(request_data)
        secure_hash = VNPayGateway._generate_signature(config.hash_secret, request_data)
        
        return f"{config.payment_url}?{query_string}&vnp_SecureHash={secure_hash}"
    
    @staticmethod
    def validate_callback(
        secret_key: str,
        response_data: Dict[str, Any]
    ) -> bool:
        """
        Validate signature từ VNPay callback
        
        Args:
            secret_key: VNPay hash secret
            response_data: Dict chứa tất cả params từ VNPay (bao gồm vnp_SecureHash)
            
        Returns:
            bool: True nếu signature hợp lệ
        """
        # Extract signature từ response
        received_hash = response_data.get('vnp_SecureHash')
        if not received_hash:
            return False
        
        # Remove signature và hash type khỏi data trước khi validate
        data_to_validate = {
            k: v for k, v in response_data.items()
            if k not in ('vnp_SecureHash', 'vnp_SecureHashType')
        }
        
        # Generate expected signature
        expected_hash = VNPayGateway._generate_signature(secret_key, data_to_validate)
        
        return received_hash == expected_hash
    
    @staticmethod
    def _build_query_string(data: Dict[str, Any]) -> str:
        """
        Build URL-encoded query string từ dict
        
        Args:
            data: Dictionary chứa key-value pairs
            
        Returns:
            str: URL-encoded query string (sorted by key)
        """
        sorted_data = sorted(data.items())
        encoded_params = [
            f"{key}={urllib.parse.quote_plus(str(val))}"
            for key, val in sorted_data
        ]
        return "&".join(encoded_params)
    
    @staticmethod
    def _generate_signature(secret_key: str, data: Dict[str, Any]) -> str:
        """
        Generate HMAC-SHA512 signature cho VNPay
        
        Args:
            secret_key: VNPay hash secret
            data: Dictionary chứa data cần ký
            
        Returns:
            str: Hex-encoded signature
        """
        # Sort data và build raw string (không encode)
        sorted_data = sorted(data.items())
        raw_data = "&".join([f"{key}={val}" for key, val in sorted_data])
        
        # HMAC-SHA512
        byte_key = secret_key.encode('utf-8')
        byte_data = raw_data.encode('utf-8')
        
        return hmac.new(byte_key, byte_data, hashlib.sha512).hexdigest()


# Backward compatibility: Keep old class name for existing code
class vnpay:
    """
    DEPRECATED: Sử dụng VNPayGateway thay thế
    
    Class này giữ lại để tương thích với code cũ.
    Sẽ xóa trong phiên bản tiếp theo.
    """
    def __init__(self):
        self.requestData = {}
        self.responseData = {}
        import warnings
        warnings.warn(
            "Class 'vnpay' is deprecated. Use 'VNPayGateway' instead.",
            DeprecationWarning,
            stacklevel=2
        )

    def get_payment_url(self, vnp_Url, secret_key):
        """Legacy method - sử dụng VNPayGateway.create_payment_url thay thế"""
        query_string = self._build_query_string_legacy(self.requestData)
        hash_value = self._hmac_sha512(secret_key, self._get_hash_data(self.requestData))
        return f"{vnp_Url}?{query_string}&vnp_SecureHash={hash_value}"

    def validate_response(self, secret_key):
        """Legacy method - sử dụng VNPayGateway.validate_callback thay thế"""
        vnp_SecureHash = self.responseData.get('vnp_SecureHash')
        data_to_check = {
            k: v for k, v in self.responseData.items()
            if k not in ('vnp_SecureHash', 'vnp_SecureHashType')
        }
        hash_value = self._hmac_sha512(secret_key, self._get_hash_data(data_to_check))
        return vnp_SecureHash == hash_value

    def _build_query_string_legacy(self, data):
        sorted_data = sorted(data.items())
        return "&".join([f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in sorted_data])

    def _get_hash_data(self, data):
        sorted_data = sorted(data.items())
        return "&".join([f"{k}={v}" for k, v in sorted_data])

    def _hmac_sha512(self, key, data):
        return hmac.new(key.encode('utf-8'), data.encode('utf-8'), hashlib.sha512).hexdigest()
    
    # Alias for backward compatibility
    _VNPayGateway__hmacsha512 = _hmac_sha512
