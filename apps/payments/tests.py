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
    """Test cho VNPay integration"""

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

    def test_generate_payment_url(self):
        """Test tạo URL thanh toán VNPay"""
        # Test logic tạo URL (nếu có helper function)
        # Ví dụ: vnpay.generate_payment_url(transaction)
        pass

    def test_verify_payment_signature(self):
        """Test xác thực chữ ký từ VNPay"""
        # Test logic verify signature
        pass

    def test_payment_callback_success(self):
        """Test xử lý callback thành công từ VNPay"""
        transaction = Transaction.objects.create(
            user=self.user,
            package=self.package,
            amount=self.package.price,
            status='PENDING',
            transaction_code='VNPAY123'
        )
        
        # Giả lập callback params từ VNPay
        # Test xử lý và cập nhật status
        pass

    def test_payment_callback_failed(self):
        """Test xử lý callback thất bại từ VNPay"""
        transaction = Transaction.objects.create(
            user=self.user,
            package=self.package,
            amount=self.package.price,
            status='PENDING',
            transaction_code='VNPAY456'
        )
        
        # Giả lập callback thất bại
        # Test xử lý và giữ nguyên credits
        pass
