from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()


class UserModelTest(TestCase):
    """Test cho User Model"""

    def setUp(self):
        self.candidate_user = User.objects.create_user(
            email='candidate@test.com',
            username='candidate@test.com',
            password='testpass123',
            full_name='Test Candidate',
            user_type='CANDIDATE'
        )
        
        self.recruiter_user = User.objects.create_user(
            email='recruiter@test.com',
            username='recruiter@test.com',
            password='testpass123',
            full_name='Test Recruiter',
            user_type='RECRUITER'
        )

    def test_user_creation(self):
        """Test tạo user thành công"""
        self.assertEqual(self.candidate_user.email, 'candidate@test.com')
        self.assertEqual(self.candidate_user.user_type, 'CANDIDATE')
        self.assertTrue(self.candidate_user.check_password('testpass123'))

    def test_user_str_representation(self):
        """Test __str__ method"""
        self.assertEqual(str(self.candidate_user), 'candidate@test.com')

    def test_user_type_choices(self):
        """Test các loại user type"""
        self.assertIn(self.candidate_user.user_type, ['CANDIDATE', 'RECRUITER', 'ADMIN'])
        self.assertEqual(self.recruiter_user.user_type, 'RECRUITER')

    def test_default_job_posting_credits(self):
        """Test credits mặc định"""
        self.assertEqual(self.candidate_user.job_posting_credits, 0)
        self.assertEqual(self.recruiter_user.job_posting_credits, 0)

    def test_membership_expires_at_default(self):
        """Test membership_expires_at mặc định là None"""
        self.assertIsNone(self.candidate_user.membership_expires_at)

    def test_has_unlimited_posting_default(self):
        """Test has_unlimited_posting mặc định là False"""
        self.assertFalse(self.candidate_user.has_unlimited_posting)

    def test_can_view_contact_default(self):
        """Test can_view_contact mặc định là False"""
        self.assertFalse(self.recruiter_user.can_view_contact)


class RegisterAPITest(APITestCase):
    """Test cho Register API"""

    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('v1:register')

    def test_register_candidate_success(self):
        """Test đăng ký candidate thành công"""
        data = {
            'email': 'newcandidate@test.com',
            'password': 'newpass123',
            'full_name': 'New Candidate',
            'user_type': 'CANDIDATE'
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='newcandidate@test.com').exists())
        
        # Candidate được active ngay
        user = User.objects.get(email='newcandidate@test.com')
        self.assertTrue(user.is_active)

    def test_register_recruiter_inactive(self):
        """Test đăng ký recruiter cần duyệt"""
        data = {
            'email': 'newrecruiter@test.com',
            'password': 'newpass123',
            'full_name': 'New Recruiter',
            'user_type': 'RECRUITER'
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Recruiter phải chờ duyệt (is_active=False)
        user = User.objects.get(email='newrecruiter@test.com')
        self.assertFalse(user.is_active)

    def test_register_duplicate_email(self):
        """Test đăng ký email trùng lặp"""
        User.objects.create_user(
            email='existing@test.com',
            username='existing@test.com',
            password='pass123',
            full_name='Existing User'
        )
        
        data = {
            'email': 'existing@test.com',
            'password': 'newpass123',
            'full_name': 'New User',
            'user_type': 'CANDIDATE'
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_password(self):
        """Test đăng ký với mật khẩu ngắn"""
        data = {
            'email': 'test@test.com',
            'password': '123',  # Quá ngắn
            'full_name': 'Test User',
            'user_type': 'CANDIDATE'
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields(self):
        """Test đăng ký thiếu trường bắt buộc"""
        data = {
            'email': 'test@test.com',
            'password': 'pass123'
            # Thiếu full_name và user_type
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginAPITest(APITestCase):
    """Test cho Login API"""

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('token_obtain_pair')
        
        # Tạo active user
        self.active_user = User.objects.create_user(
            email='active@test.com',
            username='active@test.com',
            password='testpass123',
            full_name='Active User',
            user_type='CANDIDATE',
            is_active=True
        )
        
        # Tạo inactive user (recruiter chưa duyệt)
        self.inactive_user = User.objects.create_user(
            email='inactive@test.com',
            username='inactive@test.com',
            password='testpass123',
            full_name='Inactive User',
            user_type='RECRUITER',
            is_active=False
        )

    def test_login_success(self):
        """Test đăng nhập thành công"""
        data = {
            'email': 'active@test.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user_id', response.data)
        self.assertIn('full_name', response.data)
        self.assertEqual(response.data['email'], 'active@test.com')

    def test_login_inactive_user(self):
        """Test đăng nhập với tài khoản chưa active"""
        data = {
            'email': 'inactive@test.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_wrong_password(self):
        """Test đăng nhập sai mật khẩu"""
        data = {
            'email': 'active@test.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_user(self):
        """Test đăng nhập với email không tồn tại"""
        data = {
            'email': 'nonexistent@test.com',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserProfileAPITest(APITestCase):
    """Test cho User Profile API"""

    def setUp(self):
        self.client = APIClient()
        self.profile_url = reverse('v1:user-profile')
        
        self.user = User.objects.create_user(
            email='user@test.com',
            username='user@test.com',
            password='testpass123',
            full_name='Test User',
            user_type='CANDIDATE'
        )

    def test_get_profile_authenticated(self):
        """Test lấy thông tin profile khi đã đăng nhập"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'user@test.com')
        self.assertEqual(response.data['full_name'], 'Test User')

    def test_get_profile_unauthenticated(self):
        """Test lấy profile khi chưa đăng nhập"""
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile_success(self):
        """Test cập nhật profile thành công"""
        self.client.force_authenticate(user=self.user)
        data = {
            'full_name': 'Updated Name'
        }
        response = self.client.patch(self.profile_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, 'Updated Name')

    def test_update_readonly_fields(self):
        """Test không thể cập nhật các trường read-only"""
        self.client.force_authenticate(user=self.user)
        
        original_email = self.user.email
        original_credits = self.user.job_posting_credits
        
        data = {
            'email': 'newemail@test.com',
            'job_posting_credits': 999,
            'user_type': 'ADMIN'
        }
        response = self.client.patch(self.profile_url, data, format='json')
        
        self.user.refresh_from_db()
        # Email, credits, user_type không đổi vì là read_only
        self.assertEqual(self.user.email, original_email)
        self.assertEqual(self.user.job_posting_credits, original_credits)
        self.assertNotEqual(self.user.user_type, 'ADMIN')
