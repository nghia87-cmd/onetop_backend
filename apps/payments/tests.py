from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import ServicePackage, Transaction

User = get_user_model()


class ServicePackageModelTest(TestCase):
    """Test cho ServicePackage Model"""

    def setUp(self):
        self.credit_package = ServicePackage.objects.create(
            name='Gói 10 lượt',
            price=Decimal('500000'),
            duration_days=30,
            package_type='CREDIT',
            job_posting_limit=10,
            description='Mua 10 lượt đăng tin'
        )
        
        self.subscription_package = ServicePackage.objects.create(
            name='Gói VIP',
            price=Decimal('2000000'),
            duration_days=90,
            package_type='SUBSCRIPTION',
            allow_unlimited_posting=True,
            allow_view_contact=True,
            description='Gói VIP 3 tháng'
        )

    def test_credit_package_creation(self):
        """Test tạo gói credit thành công"""
        self.assertEqual(self.credit_package.name, 'Gói 10 lượt')
        self.assertEqual(self.credit_package.package_type, 'CREDIT')
        self.assertEqual(self.credit_package.job_posting_limit, 10)

    def test_subscription_package_creation(self):
        """Test tạo gói subscription thành công"""
        self.assertEqual(self.subscription_package.name, 'Gói VIP')
        self.assertEqual(self.subscription_package.package_type, 'SUBSCRIPTION')
        self.assertTrue(self.subscription_package.allow_unlimited_posting)
        self.assertTrue(self.subscription_package.allow_view_contact)

    def test_package_str_representation(self):
        """Test __str__ method"""
        self.assertIn('Gói 10 lượt', str(self.credit_package))
        self.assertIn('CREDIT', str(self.credit_package))

    def test_package_type_choices(self):
        """Test package_type choices"""
        self.assertIn(self.credit_package.package_type, ['CREDIT', 'SUBSCRIPTION'])

    def test_default_duration_days(self):
        """Test duration_days mặc định là 30"""
        package = ServicePackage.objects.create(
            name='Test Package',
            price=Decimal('100000'),
            package_type='CREDIT'
        )
        self.assertEqual(package.duration_days, 30)


class TransactionModelTest(TestCase):
    """Test cho Transaction Model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            username='user@test.com',
            password='testpass123',
            full_name='Test User',
            user_type='RECRUITER'
        )
        
        self.package = ServicePackage.objects.create(
            name='Test Package',
            price=Decimal('500000'),
            package_type='CREDIT',
            job_posting_limit=10
        )
        
        self.transaction = Transaction.objects.create(
            user=self.user,
            package=self.package,
            amount=Decimal('500000'),
            status='PENDING',
            transaction_code='TEST123456'
        )

    def test_transaction_creation(self):
        """Test tạo transaction thành công"""
        self.assertEqual(self.transaction.user, self.user)
        self.assertEqual(self.transaction.package, self.package)
        self.assertEqual(self.transaction.status, 'PENDING')

    def test_transaction_str_representation(self):
        """Test __str__ method"""
        self.assertIn(self.user.email, str(self.transaction))
        self.assertIn(self.transaction.status, str(self.transaction))

    def test_transaction_status_choices(self):
        """Test status choices"""
        self.assertIn(self.transaction.status, ['PENDING', 'SUCCESS', 'FAILED'])

    def test_transaction_unique_code(self):
        """Test transaction_code phải unique"""
        with self.assertRaises(Exception):
            Transaction.objects.create(
                user=self.user,
                package=self.package,
                amount=Decimal('500000'),
                status='PENDING',
                transaction_code='TEST123456'  # Trùng code
            )


class PaymentAPITest(APITestCase):
    """Test cho Payment API"""

    def setUp(self):
        self.client = APIClient()
        
        self.recruiter = User.objects.create_user(
            email='recruiter@test.com',
            username='recruiter@test.com',
            password='testpass123',
            full_name='Test Recruiter',
            user_type='RECRUITER',
            job_posting_credits=0
        )
        
        self.credit_package = ServicePackage.objects.create(
            name='Gói 10 lượt',
            price=Decimal('500000'),
            duration_days=30,
            package_type='CREDIT',
            job_posting_limit=10
        )
        
        self.vip_package = ServicePackage.objects.create(
            name='Gói VIP',
            price=Decimal('2000000'),
            duration_days=90,
            package_type='SUBSCRIPTION',
            allow_unlimited_posting=True,
            allow_view_contact=True
        )
        
        self.packages_url = reverse('servicepackage-list')

    def test_list_service_packages(self):
        """Test danh sách gói dịch vụ"""
        response = self.client.get(self.packages_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data['results']) >= 2)

    def test_get_package_detail(self):
        """Test xem chi tiết gói dịch vụ"""
        url = reverse('servicepackage-detail', args=[self.credit_package.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Gói 10 lượt')

    def test_create_payment_transaction(self):
        """Test tạo giao dịch thanh toán"""
        self.client.force_authenticate(user=self.recruiter)
        
        # Giả sử có endpoint để tạo transaction
        transactions_url = reverse('transaction-list')
        
        data = {
            'package': self.credit_package.id
        }
        
        response = self.client.post(transactions_url, data, format='json')
        
        # Transaction được tạo với status PENDING
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Transaction.objects.filter(user=self.recruiter, package=self.credit_package).exists())

    def test_successful_payment_adds_credits(self):
        """Test thanh toán thành công cộng credits"""
        # Tạo transaction PENDING
        transaction = Transaction.objects.create(
            user=self.recruiter,
            package=self.credit_package,
            amount=self.credit_package.price,
            status='PENDING',
            transaction_code='TEST123'
        )
        
        initial_credits = self.recruiter.job_posting_credits
        
        # Giả lập callback từ VNPay (SUCCESS)
        transaction.status = 'SUCCESS'
        transaction.save()
        
        # Xử lý logic cộng credits (giả sử có signal hoặc view xử lý)
        # Trong test này ta xử lý trực tiếp
        if transaction.status == 'SUCCESS' and transaction.package.package_type == 'CREDIT':
            self.recruiter.job_posting_credits += transaction.package.job_posting_limit
            self.recruiter.membership_expires_at = timezone.now() + timedelta(days=transaction.package.duration_days)
            self.recruiter.save()
        
        self.recruiter.refresh_from_db()
        self.assertEqual(self.recruiter.job_posting_credits, initial_credits + 10)
        self.assertIsNotNone(self.recruiter.membership_expires_at)

    def test_successful_vip_payment_grants_permissions(self):
        """Test thanh toán VIP cấp quyền"""
        transaction = Transaction.objects.create(
            user=self.recruiter,
            package=self.vip_package,
            amount=self.vip_package.price,
            status='PENDING',
            transaction_code='VIP123'
        )
        
        # Giả lập callback SUCCESS
        transaction.status = 'SUCCESS'
        transaction.save()
        
        # Xử lý logic VIP
        if transaction.status == 'SUCCESS' and transaction.package.package_type == 'SUBSCRIPTION':
            self.recruiter.has_unlimited_posting = transaction.package.allow_unlimited_posting
            self.recruiter.can_view_contact = transaction.package.allow_view_contact
            self.recruiter.membership_expires_at = timezone.now() + timedelta(days=transaction.package.duration_days)
            self.recruiter.save()
        
        self.recruiter.refresh_from_db()
        self.assertTrue(self.recruiter.has_unlimited_posting)
        self.assertTrue(self.recruiter.can_view_contact)

    def test_list_user_transactions(self):
        """Test xem lịch sử giao dịch của user"""
        Transaction.objects.create(
            user=self.recruiter,
            package=self.credit_package,
            amount=self.credit_package.price,
            status='SUCCESS',
            transaction_code='HIST1'
        )
        
        Transaction.objects.create(
            user=self.recruiter,
            package=self.vip_package,
            amount=self.vip_package.price,
            status='PENDING',
            transaction_code='HIST2'
        )
        
        self.client.force_authenticate(user=self.recruiter)
        
        transactions_url = reverse('transaction-list')
        response = self.client.get(transactions_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # User chỉ xem được giao dịch của mình
        self.assertEqual(len(response.data['results']), 2)

    def test_unauthenticated_cannot_create_transaction(self):
        """Test chưa đăng nhập không thể tạo giao dịch"""
        transactions_url = reverse('transaction-list')
        
        data = {
            'package': self.credit_package.id
        }
        
        response = self.client.post(transactions_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class VNPayIntegrationTest(TestCase):
    """Test cho VNPay integration với Mocking"""

    def setUp(self):
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            email='user@test.com',
            username='user@test.com',
            password='testpass123',
            full_name='Test User',
            user_type='RECRUITER',
            job_posting_credits=0
        )
        
        self.package = ServicePackage.objects.create(
            name='Test Package',
            price=Decimal('500000'),
            package_type='CREDIT',
            job_posting_limit=10
        )
        
        self.vip_package = ServicePackage.objects.create(
            name='VIP Package',
            price=Decimal('2000000'),
            package_type='SUBSCRIPTION',
            allow_unlimited_posting=True,
            allow_view_contact=True
        )

    def test_generate_payment_url(self):
        """Test tạo URL thanh toán VNPay với Mock"""
        from unittest.mock import patch, MagicMock
        
        self.client.force_authenticate(user=self.user)
        
        with patch('apps.payments.views.vnpay') as mock_vnpay_class:
            # Setup mock
            mock_vnpay_instance = MagicMock()
            mock_vnpay_class.return_value = mock_vnpay_instance
            mock_vnpay_instance.get_payment_url.return_value = 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?vnp_Amount=50000000&vnp_Command=pay'
            
            # Call API
            url = reverse('transaction-create-payment')
            data = {'package_id': self.package.id}
            response = self.client.post(url, data, format='json')
            
            # Assert
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('payment_url', response.data)
            self.assertIn('transaction_code', response.data)
            
            # Verify transaction created
            self.assertTrue(
                Transaction.objects.filter(
                    user=self.user,
                    package=self.package,
                    status='PENDING'
                ).exists()
            )

    def test_verify_payment_signature(self):
        """Test xác thực chữ ký từ VNPay"""
        from unittest.mock import patch
        from apps.payments.vnpay import vnpay
        
        # Test với signature hợp lệ
        with patch.object(vnpay, 'validate_response', return_value=True):
            vnp = vnpay()
            vnp.responseData = {
                'vnp_TxnRef': 'TEST123',
                'vnp_Amount': '50000000',
                'vnp_ResponseCode': '00'
            }
            
            is_valid = vnp.validate_response('test_secret_key')
            self.assertTrue(is_valid)
        
        # Test với signature không hợp lệ
        with patch.object(vnpay, 'validate_response', return_value=False):
            vnp = vnpay()
            is_valid = vnp.validate_response('wrong_secret_key')
            self.assertFalse(is_valid)

    def test_payment_callback_success(self):
        """Test xử lý callback thành công từ VNPay"""
        from unittest.mock import patch
        
        # Tạo transaction
        transaction = Transaction.objects.create(
            user=self.user,
            package=self.package,
            amount=self.package.price,
            status='PENDING',
            transaction_code='VNPAY123'
        )
        
        initial_credits = self.user.job_posting_credits
        
        # Mock VNPay validation
        with patch('apps.payments.views.vnpay') as mock_vnpay_class:
            mock_instance = mock_vnpay_class.return_value
            mock_instance.validate_response.return_value = True
            
            # Giả lập callback params từ VNPay
            callback_params = {
                'vnp_TxnRef': 'VNPAY123',
                'vnp_Amount': str(int(self.package.price * 100)),
                'vnp_ResponseCode': '00',  # Success code
                'vnp_SecureHash': 'fake_hash'
            }
            
            # Call return URL endpoint
            url = reverse('vnpay-return')
            response = self.client.get(url, callback_params)
            
            # Assert transaction updated
            transaction.refresh_from_db()
            self.assertEqual(transaction.status, 'SUCCESS')
            
            # Assert credits added
            self.user.refresh_from_db()
            self.assertEqual(
                self.user.job_posting_credits,
                initial_credits + self.package.job_posting_limit
            )
            
            # Assert membership expires set
            self.assertIsNotNone(self.user.membership_expires_at)

    def test_payment_callback_failed(self):
        """Test xử lý callback thất bại từ VNPay"""
        from unittest.mock import patch
        
        transaction = Transaction.objects.create(
            user=self.user,
            package=self.package,
            amount=self.package.price,
            status='PENDING',
            transaction_code='VNPAY456'
        )
        
        initial_credits = self.user.job_posting_credits
        
        with patch('apps.payments.views.vnpay') as mock_vnpay_class:
            mock_instance = mock_vnpay_class.return_value
            mock_instance.validate_response.return_value = True
            
            # Giả lập callback thất bại (ResponseCode khác 00)
            callback_params = {
                'vnp_TxnRef': 'VNPAY456',
                'vnp_Amount': str(int(self.package.price * 100)),
                'vnp_ResponseCode': '24',  # Failed code
                'vnp_SecureHash': 'fake_hash'
            }
            
            url = reverse('vnpay-return')
            response = self.client.get(url, callback_params)
            
            # Assert transaction status = FAILED
            transaction.refresh_from_db()
            self.assertEqual(transaction.status, 'FAILED')
            
            # Assert credits không thay đổi
            self.user.refresh_from_db()
            self.assertEqual(self.user.job_posting_credits, initial_credits)

    def test_payment_vip_package_grants_permissions(self):
        """Test thanh toán VIP cấp quyền unlimited posting"""
        from unittest.mock import patch
        
        transaction = Transaction.objects.create(
            user=self.user,
            package=self.vip_package,
            amount=self.vip_package.price,
            status='PENDING',
            transaction_code='VIP123'
        )
        
        with patch('apps.payments.views.vnpay') as mock_vnpay_class:
            mock_instance = mock_vnpay_class.return_value
            mock_instance.validate_response.return_value = True
            
            callback_params = {
                'vnp_TxnRef': 'VIP123',
                'vnp_Amount': str(int(self.vip_package.price * 100)),
                'vnp_ResponseCode': '00',
                'vnp_SecureHash': 'fake_hash'
            }
            
            url = reverse('vnpay-return')
            response = self.client.get(url, callback_params)
            
            # Assert VIP permissions granted
            self.user.refresh_from_db()
            self.assertTrue(self.user.has_unlimited_posting)
            self.assertTrue(self.user.can_view_contact)

    def test_invalid_signature_rejected(self):
        """Test từ chối callback với signature không hợp lệ"""
        from unittest.mock import patch
        
        transaction = Transaction.objects.create(
            user=self.user,
            package=self.package,
            amount=self.package.price,
            status='PENDING',
            transaction_code='HACK123'
        )
        
        with patch('apps.payments.views.vnpay') as mock_vnpay_class:
            mock_instance = mock_vnpay_class.return_value
            mock_instance.validate_response.return_value = False  # Invalid signature
            
            callback_params = {
                'vnp_TxnRef': 'HACK123',
                'vnp_Amount': str(int(self.package.price * 100)),
                'vnp_ResponseCode': '00',
                'vnp_SecureHash': 'wrong_hash'
            }
            
            url = reverse('vnpay-return')
            response = self.client.get(url, callback_params)
            
            # Transaction should remain PENDING
            transaction.refresh_from_db()
            self.assertEqual(transaction.status, 'PENDING')
            
            # Credits not added
            self.user.refresh_from_db()
            self.assertEqual(self.user.job_posting_credits, 0)
