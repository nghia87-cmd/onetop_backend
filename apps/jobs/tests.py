from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Job, SavedJob
from apps.companies.models import Company

User = get_user_model()


class JobModelTest(TestCase):
    """Test cho Job Model"""

    def setUp(self):
        self.recruiter = User.objects.create_user(
            email='recruiter@test.com',
            username='recruiter@test.com',
            password='testpass123',
            full_name='Test Recruiter',
            user_type='RECRUITER'
        )
        
        self.company = Company.objects.create(
            name='Test Company',
            description='Test Description',
            address='Test Address',
            owner=self.recruiter
        )
        
        self.job = Job.objects.create(
            title='Python Developer',
            company=self.company,
            location='Hà Nội',
            job_type='FULL_TIME',
            salary_min=1000,
            salary_max=2000,
            description='Test job description',
            requirements='Python, Django',
            benefits='Competitive salary',
            deadline=timezone.now().date() + timedelta(days=30),
            status='PUBLISHED'
        )

    def test_job_creation(self):
        """Test tạo job thành công"""
        self.assertEqual(self.job.title, 'Python Developer')
        self.assertEqual(self.job.company, self.company)
        self.assertEqual(self.job.status, 'PUBLISHED')

    def test_job_str_representation(self):
        """Test __str__ method"""
        expected = f"Python Developer - {self.company.name}"
        self.assertEqual(str(self.job), expected)

    def test_job_slug_generation(self):
        """Test slug được tạo tự động"""
        self.assertIsNotNone(self.job.slug)
        self.assertIn('python-developer', self.job.slug.lower())

    def test_job_default_views_count(self):
        """Test views_count mặc định là 0"""
        self.assertEqual(self.job.views_count, 0)

    def test_job_type_choices(self):
        """Test job_type choices"""
        self.assertIn(self.job.job_type, ['FULL_TIME', 'PART_TIME', 'FREELANCE', 'INTERNSHIP'])

    def test_job_status_choices(self):
        """Test status choices"""
        self.assertIn(self.job.status, ['DRAFT', 'PUBLISHED', 'CLOSED'])

    def test_negotiable_salary(self):
        """Test lương thỏa thuận"""
        job = Job.objects.create(
            title='Negotiable Job',
            company=self.company,
            location='TP.HCM',
            job_type='FULL_TIME',
            is_negotiable=True,
            description='Test',
            requirements='Test',
            benefits='Test',
            deadline=timezone.now().date() + timedelta(days=30)
        )
        self.assertTrue(job.is_negotiable)
        self.assertIsNone(job.salary_min)
        self.assertIsNone(job.salary_max)


class JobAPITest(APITestCase):
    """Test cho Job API"""

    def setUp(self):
        self.client = APIClient()
        
        # Tạo recruiter với credits và membership
        self.recruiter = User.objects.create_user(
            email='recruiter@test.com',
            username='recruiter@test.com',
            password='testpass123',
            full_name='Test Recruiter',
            user_type='RECRUITER',
            job_posting_credits=5,
            membership_expires_at=timezone.now() + timedelta(days=30)
        )
        
        # Tạo recruiter VIP
        self.vip_recruiter = User.objects.create_user(
            email='vip@test.com',
            username='vip@test.com',
            password='testpass123',
            full_name='VIP Recruiter',
            user_type='RECRUITER',
            has_unlimited_posting=True,
            membership_expires_at=timezone.now() + timedelta(days=30)
        )
        
        self.candidate = User.objects.create_user(
            email='candidate@test.com',
            username='candidate@test.com',
            password='testpass123',
            full_name='Test Candidate',
            user_type='CANDIDATE'
        )
        
        self.company = Company.objects.create(
            name='Test Company',
            description='Test Description',
            address='Test Address',
            owner=self.recruiter
        )
        
        self.vip_company = Company.objects.create(
            name='VIP Company',
            description='VIP Description',
            address='VIP Address',
            owner=self.vip_recruiter
        )
        
        self.job = Job.objects.create(
            title='Python Developer',
            company=self.company,
            location='Hà Nội',
            job_type='FULL_TIME',
            salary_min=1000,
            salary_max=2000,
            description='Test job description',
            requirements='Python, Django',
            benefits='Competitive salary',
            deadline=timezone.now().date() + timedelta(days=30),
            status='PUBLISHED'
        )
        
        # Router registers as 'list-list' because path is r'list'
        # Should be job-list if we change router.register(r'', JobViewSet)
        self.jobs_url = reverse('v1:job-list')

    def test_list_jobs_public(self):
        """Test danh sách job công khai"""
        response = self.client.get(self.jobs_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response is paginated dict with 'results' key
        self.assertIn('results', response.data)
        self.assertTrue(len(response.data['results']) > 0)

    def test_list_jobs_filter_by_location(self):
        """Test filter job theo location"""
        response = self.client.get(self.jobs_url, {'location': 'Hà Nội'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for job in response.data['results']:
            self.assertEqual(job['location'], 'Hà Nội')

    def test_list_jobs_filter_by_job_type(self):
        """Test filter job theo job_type"""
        response = self.client.get(self.jobs_url, {'job_type': 'FULL_TIME'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for job in response.data['results']:
            self.assertEqual(job['job_type'], 'FULL_TIME')

    def test_create_job_success_with_credits(self):
        """Test tạo job thành công với credits"""
        self.client.force_authenticate(user=self.recruiter)
        
        initial_credits = self.recruiter.job_posting_credits
        
        data = {
            'title': 'New Job',
            'company': self.company.pkid,  # Use pkid (primary key), not id (UUID)
            'location': 'TP.HCM',
            'job_type': 'FULL_TIME',
            'salary_min': 1500,
            'salary_max': 2500,
            'is_negotiable': False,  # Required field
            'description': 'New job description',
            'requirements': 'Python, FastAPI',
            'benefits': 'Benefits',
            'deadline': (timezone.now().date() + timedelta(days=30)).isoformat()
        }
        
        response = self.client.post(self.jobs_url, data)
        
        # DEBUG: Print if failed
        if response.status_code != status.HTTP_201_CREATED:
            print(f"\n=== DEBUG test_create_job_success_with_credits ===")
            print(f"Status: {response.status_code}")
            print(f"Data: {response.data}")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Kiểm tra credits đã bị trừ
        self.recruiter.refresh_from_db()
        self.assertEqual(self.recruiter.job_posting_credits, initial_credits - 1)

    def test_create_job_vip_no_credit_deduction(self):
        """Test VIP tạo job không trừ credits"""
        self.client.force_authenticate(user=self.vip_recruiter)
        
        data = {
            'title': 'VIP Job',
            'company': self.vip_company.pkid,
            'location': 'TP.HCM',
            'job_type': 'FULL_TIME',
            'salary_min': 2000,
            'salary_max': 3000,
            'is_negotiable': False,
            'description': 'VIP job description',
            'requirements': 'Test',
            'benefits': 'Test',
            'requirements': 'VIP requirements',
            'benefits': 'VIP benefits',
            'deadline': (timezone.now().date() + timedelta(days=30)).isoformat()
        }
        
        response = self.client.post(self.jobs_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # VIP không bị trừ credits
        self.vip_recruiter.refresh_from_db()
        self.assertEqual(self.vip_recruiter.job_posting_credits, 0)

    def test_create_job_no_credits(self):
        """Test tạo job khi hết credits"""
        self.recruiter.job_posting_credits = 0
        self.recruiter.save()
        
        self.client.force_authenticate(user=self.recruiter)
        
        data = {
            'title': 'No Credit Job',
            'company': self.company.pkid,
            'location': 'Hà Nội',
            'job_type': 'FULL_TIME',
            'salary_min': 1000,
            'salary_max': 1500,
            'is_negotiable': False,
            'description': 'Test',
            'requirements': 'Test',
            'benefits': 'Test',
            'deadline': (timezone.now().date() + timedelta(days=30)).isoformat()
        }
        
        response = self.client.post(self.jobs_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_job_expired_membership(self):
        """Test tạo job khi membership đã hết hạn"""
        self.recruiter.membership_expires_at = timezone.now() - timedelta(days=1)
        self.recruiter.save()
        
        self.client.force_authenticate(user=self.recruiter)
        
        data = {
            'title': 'Expired Job',
            'company': self.company.pkid,
            'location': 'Hà Nội',
            'job_type': 'FULL_TIME',
            'salary_min': 1000,
            'salary_max': 1500,
            'is_negotiable': False,
            'description': 'Test',
            'requirements': 'Test',
            'benefits': 'Test',
            'deadline': (timezone.now().date() + timedelta(days=30)).isoformat()
        }
        
        response = self.client.post(self.jobs_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_job_wrong_company_owner(self):
        """Test tạo job cho công ty không sở hữu"""
        other_recruiter = User.objects.create_user(
            email='other@test.com',
            username='other@test.com',
            password='testpass123',
            full_name='Other Recruiter',
            user_type='RECRUITER',
            job_posting_credits=5,
            membership_expires_at=timezone.now() + timedelta(days=30)
        )
        
        self.client.force_authenticate(user=other_recruiter)
        
        data = {
            'title': 'Unauthorized Job',
            'company': self.company.pkid,  # Công ty của recruiter khác
            'location': 'Hà Nội',
            'job_type': 'FULL_TIME',
            'salary_min': 1000,
            'salary_max': 1500,
            'is_negotiable': False,
            'description': 'Test',
            'requirements': 'Test',
            'benefits': 'Test',
            'deadline': (timezone.now().date() + timedelta(days=30)).isoformat()
        }
        
        response = self.client.post(self.jobs_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_candidate_cannot_create_job(self):
        """Test candidate không thể tạo job"""
        self.client.force_authenticate(user=self.candidate)
        
        data = {
            'title': 'Candidate Job',
            'company': self.company.pkid,
            'location': 'Hà Nội',
            'job_type': 'FULL_TIME',
            'description': 'Test',
            'requirements': 'Test',
            'benefits': 'Test',
            'deadline': (timezone.now().date() + timedelta(days=30)).isoformat(),
            'status': 'PUBLISHED'
        }
        
        response = self.client.post(self.jobs_url, data)
        
        # Candidate không có company nên sẽ thất bại
        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)


class SavedJobAPITest(APITestCase):
    """Test cho Saved Job API"""

    def setUp(self):
        self.client = APIClient()
        
        self.candidate = User.objects.create_user(
            email='candidate@test.com',
            username='candidate@test.com',
            password='testpass123',
            full_name='Test Candidate',
            user_type='CANDIDATE'
        )
        
        self.recruiter = User.objects.create_user(
            email='recruiter@test.com',
            username='recruiter@test.com',
            password='testpass123',
            full_name='Test Recruiter',
            user_type='RECRUITER'
        )
        
        self.company = Company.objects.create(
            name='Test Company',
            description='Test Description',
            address='Test Address',
            owner=self.recruiter
        )
        
        self.job = Job.objects.create(
            title='Python Developer',
            company=self.company,
            location='Hà Nội',
            job_type='FULL_TIME',
            description='Test job description',
            requirements='Python, Django',
            benefits='Competitive salary',
            deadline=timezone.now().date() + timedelta(days=30),
            status='PUBLISHED'
        )
        
        self.saved_jobs_url = reverse('v1:saved-jobs-list')

    def test_save_job_success(self):
        """Test lưu job thành công"""
        self.client.force_authenticate(user=self.candidate)
        
        data = {
            'job': self.job.id
        }
        
        response = self.client.post(self.saved_jobs_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(SavedJob.objects.filter(user=self.candidate, job=self.job).exists())

    def test_save_job_duplicate(self):
        """Test không thể lưu job trùng lặp"""
        SavedJob.objects.create(user=self.candidate, job=self.job)
        
        self.client.force_authenticate(user=self.candidate)
        
        data = {
            'job': self.job.id
        }
        
        response = self.client.post(self.saved_jobs_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_saved_jobs(self):
        """Test danh sách job đã lưu"""
        SavedJob.objects.create(user=self.candidate, job=self.job)
        
        self.client.force_authenticate(user=self.candidate)
        
        response = self.client.get(self.saved_jobs_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_delete_saved_job(self):
        """Test xóa job đã lưu"""
        saved_job = SavedJob.objects.create(user=self.candidate, job=self.job)
        
        self.client.force_authenticate(user=self.candidate)
        
        url = reverse('v1:saved-jobs-detail', args=[saved_job.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SavedJob.objects.filter(id=saved_job.id).exists())

    def test_unauthenticated_cannot_save_job(self):
        """Test chưa đăng nhập không thể lưu job"""
        data = {
            'job': self.job.id
        }
        
        response = self.client.post(self.saved_jobs_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
