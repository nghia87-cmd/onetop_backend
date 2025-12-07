"""
Test Protected Media Access
Verify that CV/Resume files are properly protected
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from rest_framework import status
from apps.users.models import User
from apps.resumes.models import Resume
from apps.applications.models import Application
from apps.jobs.models import Job
from apps.companies.models import Company


@override_settings(
    ELASTICSEARCH_DSL_AUTOSYNC=False,
    ELASTICSEARCH_DSL_AUTO_REFRESH=False,
    ELASTICSEARCH_DSL_SIGNAL_PROCESSOR='django_elasticsearch_dsl.signals.BaseSignalProcessor'
)
class ProtectedMediaAccessTest(TestCase):
    """Test secure file download endpoints"""
    
    def setUp(self):
        # Create candidate with resume
        self.candidate = User.objects.create_user(
            email='candidate@test.com',
            username='candidate@test.com',
            password='testpass123',
            user_type='CANDIDATE',
            full_name='Test Candidate'
        )
        
        self.resume = Resume.objects.create(
            user=self.candidate,
            title='Software Engineer',
            is_primary=True
        )
        
        # Create recruiter with company and job
        self.recruiter = User.objects.create_user(
            email='recruiter@test.com',
            username='recruiter@test.com',
            password='testpass123',
            user_type='RECRUITER',
            full_name='Test Recruiter',
            job_posting_credits=10
        )
        
        self.company = Company.objects.create(
            name='Test Company',
            owner=self.recruiter,
            description='Test Description',
            address='Test Address'
        )
        
        self.job = Job.objects.create(
            title='Python Developer',
            company=self.company,
            location='Hanoi',
            description='Test job',
            requirements='Python',
            benefits='Benefits',
            deadline='2025-12-31'
        )
        
        # Create application
        self.application = Application.objects.create(
            candidate=self.candidate,
            job=self.job,
            status='PENDING'
        )
        
        # Create unrelated user
        self.other_user = User.objects.create_user(
            email='other@test.com',
            username='other@test.com',
            password='testpass123',
            user_type='CANDIDATE',
            full_name='Other User'
        )
        
        self.client = Client()
    
    def test_resume_download_by_owner(self):
        """Resume owner can download their own resume"""
        self.client.force_login(self.candidate)
        
        url = reverse('download-resume-pdf', args=[self.resume.id])
        response = self.client.get(url)
        
        # Should not be forbidden
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_resume_download_by_unauthorized_user(self):
        """Unauthorized user cannot download resume"""
        self.client.force_login(self.other_user)
        
        url = reverse('download-resume-pdf', args=[self.resume.id])
        response = self.client.get(url)
        
        # Should be forbidden (401 or 403)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_application_download_by_job_recruiter(self):
        """Job owner recruiter can download application CV"""
        self.client.force_login(self.recruiter)
        
        url = reverse('download-application-cv', args=[self.application.id])
        response = self.client.get(url)
        
        # Should not be forbidden
        self.assertNotEqual(response.status_code, status.HTTP_403_FORBIDDEN)
