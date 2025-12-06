"""
Pytest configuration and shared fixtures for Django tests
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.utils import timezone
from datetime import timedelta
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal

from apps.companies.models import Company
from apps.jobs.models import Job
from apps.payments.models import ServicePackage, Transaction

User = get_user_model()


@pytest.fixture
def api_client():
    """Fixture cho APIClient"""
    return APIClient()


@pytest.fixture
def candidate_user(db):
    """Fixture tạo candidate user"""
    return User.objects.create_user(
        email='candidate@test.com',
        username='candidate@test.com',
        password='testpass123',
        full_name='Test Candidate',
        user_type='CANDIDATE'
    )


@pytest.fixture
def recruiter_user(db):
    """Fixture tạo recruiter user"""
    return User.objects.create_user(
        email='recruiter@test.com',
        username='recruiter@test.com',
        password='testpass123',
        full_name='Test Recruiter',
        user_type='RECRUITER',
        job_posting_credits=5,
        membership_expires_at=timezone.now() + timedelta(days=30)
    )


@pytest.fixture
def vip_recruiter_user(db):
    """Fixture tạo VIP recruiter user"""
    return User.objects.create_user(
        email='vip@test.com',
        username='vip@test.com',
        password='testpass123',
        full_name='VIP Recruiter',
        user_type='RECRUITER',
        has_unlimited_posting=True,
        can_view_contact=True,
        membership_expires_at=timezone.now() + timedelta(days=90)
    )


@pytest.fixture
def admin_user(db):
    """Fixture tạo admin user"""
    return User.objects.create_superuser(
        email='admin@test.com',
        username='admin@test.com',
        password='admin123',
        full_name='Admin User',
        user_type='ADMIN'
    )


@pytest.fixture
def company(db, recruiter_user):
    """Fixture tạo company"""
    return Company.objects.create(
        name='Test Company',
        description='A test company',
        address='123 Test Street',
        website='https://testcompany.com',
        owner=recruiter_user
    )


@pytest.fixture
def job(db, company):
    """Fixture tạo job"""
    return Job.objects.create(
        title='Python Developer',
        company=company,
        location='Hà Nội',
        job_type='FULL_TIME',
        salary_min=1000,
        salary_max=2000,
        description='Test job description',
        requirements='Python, Django, REST API',
        benefits='Competitive salary, insurance',
        deadline=timezone.now().date() + timedelta(days=30),
        status='PUBLISHED'
    )


@pytest.fixture
def draft_job(db, company):
    """Fixture tạo draft job"""
    return Job.objects.create(
        title='Draft Job',
        company=company,
        location='TP.HCM',
        job_type='PART_TIME',
        description='Draft job description',
        requirements='Test requirements',
        benefits='Test benefits',
        deadline=timezone.now().date() + timedelta(days=30),
        status='DRAFT'
    )


@pytest.fixture
def cv_file():
    """Fixture tạo CV file giả"""
    return SimpleUploadedFile(
        "test_cv.pdf",
        b"PDF file content here",
        content_type="application/pdf"
    )


@pytest.fixture
def credit_package(db):
    """Fixture tạo credit package"""
    return ServicePackage.objects.create(
        name='Gói 10 lượt',
        price=Decimal('500000'),
        duration_days=30,
        package_type='CREDIT',
        job_posting_limit=10,
        description='Mua 10 lượt đăng tin'
    )


@pytest.fixture
def vip_package(db):
    """Fixture tạo VIP subscription package"""
    return ServicePackage.objects.create(
        name='Gói VIP 3 tháng',
        price=Decimal('2000000'),
        duration_days=90,
        package_type='SUBSCRIPTION',
        allow_unlimited_posting=True,
        allow_view_contact=True,
        description='Gói VIP với quyền lợi cao cấp'
    )


@pytest.fixture
def pending_transaction(db, recruiter_user, credit_package):
    """Fixture tạo pending transaction"""
    return Transaction.objects.create(
        user=recruiter_user,
        package=credit_package,
        amount=credit_package.price,
        status='PENDING',
        transaction_code=f'TEST{timezone.now().timestamp()}'
    )


@pytest.fixture
def authenticated_client(api_client, recruiter_user):
    """Fixture cho authenticated API client"""
    api_client.force_authenticate(user=recruiter_user)
    return api_client


@pytest.fixture
def candidate_client(api_client, candidate_user):
    """Fixture cho candidate API client"""
    api_client.force_authenticate(user=candidate_user)
    return api_client


# Database fixtures
@pytest.fixture(scope='session')
def django_db_setup():
    """Setup database for tests"""
    pass


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all tests"""
    pass
