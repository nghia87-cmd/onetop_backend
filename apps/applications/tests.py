from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import Application, InterviewSchedule
from apps.jobs.models import Job
from apps.companies.models import Company

User = get_user_model()


class ApplicationModelTest(TestCase):
    """Test cho Application Model"""

    def setUp(self):
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
        
        # Tạo file CV giả
        self.cv_file = SimpleUploadedFile(
            "test_cv.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        self.application = Application.objects.create(
            job=self.job,
            candidate=self.candidate,
            cv_file=self.cv_file,
            cover_letter='Test cover letter',
            status='PENDING'
        )

    def test_application_creation(self):
        """Test tạo application thành công"""
        self.assertEqual(self.application.job, self.job)
        self.assertEqual(self.application.candidate, self.candidate)
        self.assertEqual(self.application.status, 'PENDING')

    def test_application_str_representation(self):
        """Test __str__ method"""
        expected = f"{self.candidate.full_name} applied to {self.job.title}"
        self.assertEqual(str(self.application), expected)

    def test_application_unique_constraint(self):
        """Test không thể nộp 2 lần cho cùng 1 job"""
        cv_file2 = SimpleUploadedFile(
            "test_cv2.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        with self.assertRaises(Exception):
            Application.objects.create(
                job=self.job,
                candidate=self.candidate,
                cv_file=cv_file2
            )

    def test_application_status_choices(self):
        """Test status choices"""
        self.assertIn(self.application.status, ['PENDING', 'VIEWED', 'INTERVIEW', 'REJECTED', 'ACCEPTED'])

    def test_application_default_status(self):
        """Test status mặc định là PENDING"""
        self.assertEqual(self.application.status, 'PENDING')


class ApplicationAPITest(APITestCase):
    """Test cho Application API"""

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
        
        self.applications_url = reverse('application-list')

    def test_create_application_success(self):
        """Test tạo đơn ứng tuyển thành công"""
        self.client.force_authenticate(user=self.candidate)
        
        cv_file = SimpleUploadedFile(
            "test_cv.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        data = {
            'job': self.job.id,
            'cv_file': cv_file,
            'cover_letter': 'I am very interested in this position'
        }
        
        response = self.client.post(self.applications_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Application.objects.filter(job=self.job, candidate=self.candidate).exists())

    def test_create_application_duplicate(self):
        """Test không thể nộp đơn trùng lặp"""
        cv_file1 = SimpleUploadedFile(
            "test_cv1.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        Application.objects.create(
            job=self.job,
            candidate=self.candidate,
            cv_file=cv_file1
        )
        
        self.client.force_authenticate(user=self.candidate)
        
        cv_file2 = SimpleUploadedFile(
            "test_cv2.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        data = {
            'job': self.job.id,
            'cv_file': cv_file2,
            'cover_letter': 'Second application'
        }
        
        response = self.client.post(self.applications_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_candidate_list_own_applications(self):
        """Test candidate chỉ xem được đơn của mình"""
        cv_file = SimpleUploadedFile(
            "test_cv.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        Application.objects.create(
            job=self.job,
            candidate=self.candidate,
            cv_file=cv_file
        )
        
        # Tạo candidate khác
        other_candidate = User.objects.create_user(
            email='other@test.com',
            username='other@test.com',
            password='testpass123',
            full_name='Other Candidate',
            user_type='CANDIDATE'
        )
        
        cv_file2 = SimpleUploadedFile(
            "test_cv2.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        Application.objects.create(
            job=self.job,
            candidate=other_candidate,
            cv_file=cv_file2
        )
        
        self.client.force_authenticate(user=self.candidate)
        response = self.client.get(self.applications_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_recruiter_list_company_applications(self):
        """Test recruiter xem được đơn ứng tuyển vào công ty của mình"""
        cv_file = SimpleUploadedFile(
            "test_cv.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        Application.objects.create(
            job=self.job,
            candidate=self.candidate,
            cv_file=cv_file
        )
        
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.get(self.applications_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data['results']) > 0)

    def test_update_application_status_by_recruiter(self):
        """Test recruiter cập nhật trạng thái đơn"""
        cv_file = SimpleUploadedFile(
            "test_cv.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        application = Application.objects.create(
            job=self.job,
            candidate=self.candidate,
            cv_file=cv_file
        )
        
        self.client.force_authenticate(user=self.recruiter)
        
        url = reverse('application-update-status', args=[application.id])
        data = {
            'status': 'INTERVIEW',
            'note': 'Scheduled for interview'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        application.refresh_from_db()
        self.assertEqual(application.status, 'INTERVIEW')
        self.assertEqual(application.note, 'Scheduled for interview')

    def test_candidate_cannot_update_status(self):
        """Test candidate không thể cập nhật status"""
        cv_file = SimpleUploadedFile(
            "test_cv.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        application = Application.objects.create(
            job=self.job,
            candidate=self.candidate,
            cv_file=cv_file
        )
        
        self.client.force_authenticate(user=self.candidate)
        
        url = reverse('application-update-status', args=[application.id])
        data = {
            'status': 'ACCEPTED'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class InterviewScheduleModelTest(TestCase):
    """Test cho InterviewSchedule Model"""

    def setUp(self):
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
        
        cv_file = SimpleUploadedFile(
            "test_cv.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        self.application = Application.objects.create(
            job=self.job,
            candidate=self.candidate,
            cv_file=cv_file
        )
        
        self.interview = InterviewSchedule.objects.create(
            application=self.application,
            interview_date=timezone.now() + timedelta(days=3),
            duration_minutes=60,
            location='Test Office',
            status='SCHEDULED'
        )

    def test_interview_creation(self):
        """Test tạo lịch phỏng vấn thành công"""
        self.assertEqual(self.interview.application, self.application)
        self.assertEqual(self.interview.status, 'SCHEDULED')

    def test_interview_str_representation(self):
        """Test __str__ method"""
        self.assertIn(self.candidate.full_name, str(self.interview))

    def test_interview_default_duration(self):
        """Test duration mặc định là 60 phút"""
        self.assertEqual(self.interview.duration_minutes, 60)

    def test_interview_status_choices(self):
        """Test status choices"""
        self.assertIn(self.interview.status, ['SCHEDULED', 'COMPLETED', 'CANCELLED'])


class InterviewScheduleAPITest(APITestCase):
    """Test cho InterviewSchedule API"""

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
        
        cv_file = SimpleUploadedFile(
            "test_cv.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        self.application = Application.objects.create(
            job=self.job,
            candidate=self.candidate,
            cv_file=cv_file,
            status='PENDING'
        )
        
        self.interview_url = reverse('interviewschedule-list')

    def test_create_interview_success(self):
        """Test recruiter tạo lịch phỏng vấn thành công"""
        self.client.force_authenticate(user=self.recruiter)
        
        interview_date = (timezone.now() + timedelta(days=3)).isoformat()
        
        data = {
            'application': self.application.id,
            'interview_date': interview_date,
            'duration_minutes': 90,
            'location': 'Head Office',
            'meeting_link': 'https://meet.google.com/test',
            'note': 'Please bring your laptop'
        }
        
        response = self.client.post(self.interview_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Kiểm tra application status đã chuyển sang INTERVIEW
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'INTERVIEW')

    def test_candidate_cannot_create_interview(self):
        """Test candidate không thể tạo lịch phỏng vấn"""
        self.client.force_authenticate(user=self.candidate)
        
        interview_date = (timezone.now() + timedelta(days=3)).isoformat()
        
        data = {
            'application': self.application.id,
            'interview_date': interview_date
        }
        
        response = self.client.post(self.interview_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_recruiter_list_own_interviews(self):
        """Test recruiter xem danh sách lịch phỏng vấn của mình"""
        InterviewSchedule.objects.create(
            application=self.application,
            interview_date=timezone.now() + timedelta(days=3)
        )
        
        self.client.force_authenticate(user=self.recruiter)
        response = self.client.get(self.interview_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data['results']) > 0)

    def test_candidate_list_own_interviews(self):
        """Test candidate xem danh sách lịch phỏng vấn của mình"""
        InterviewSchedule.objects.create(
            application=self.application,
            interview_date=timezone.now() + timedelta(days=3)
        )
        
        self.client.force_authenticate(user=self.candidate)
        response = self.client.get(self.interview_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data['results']) > 0)
