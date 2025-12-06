"""
Pytest-style tests cho Jobs app
Refactored từ APITestCase sang function-based tests với fixtures
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from apps.jobs.models import Job, SavedJob
from apps.companies.models import Company

User = get_user_model()


# ==========================================
# MODEL TESTS - Job
# ==========================================

@pytest.mark.django_db
def test_job_creation(job):
    """Test tạo job thành công"""
    assert job.title == 'Python Developer'
    assert job.status == 'PUBLISHED'
    assert job.company is not None


@pytest.mark.django_db
def test_job_str_representation(job):
    """Test __str__ method"""
    expected = f"{job.title} - {job.company.name}"
    assert str(job) == expected


@pytest.mark.django_db
def test_job_slug_generation(job):
    """Test slug được tạo tự động"""
    assert job.slug is not None
    assert 'python-developer' in job.slug.lower()


@pytest.mark.django_db
def test_job_default_views_count(job):
    """Test views_count mặc định là 0"""
    assert job.views_count == 0


@pytest.mark.django_db
def test_job_type_choices(job):
    """Test job_type choices"""
    assert job.job_type in ['FULL_TIME', 'PART_TIME', 'FREELANCE', 'INTERNSHIP']


@pytest.mark.django_db
def test_job_status_choices(job):
    """Test status choices"""
    assert job.status in ['DRAFT', 'PUBLISHED', 'CLOSED']


@pytest.mark.django_db
def test_negotiable_salary(company):
    """Test lương thỏa thuận"""
    job = Job.objects.create(
        title='Negotiable Job',
        company=company,
        location='Hà Nội',
        job_type='FULL_TIME',
        description='Test description',
        requirements='Test requirements',
        is_salary_negotiable=True,
        deadline=timezone.now().date() + timedelta(days=30),
    )
    
    assert job.is_salary_negotiable
    assert job.salary_min is None or job.salary_min == 0
    assert job.salary_max is None or job.salary_max == 0


@pytest.mark.django_db
def test_job_deadline_validation(company):
    """Test deadline phải ở tương lai"""
    past_deadline = timezone.now().date() - timedelta(days=1)
    
    job = Job.objects.create(
        title='Past Deadline Job',
        company=company,
        location='Test',
        job_type='FULL_TIME',
        description='Test',
        requirements='Test',
        deadline=past_deadline,
    )
    
    # Job model có thể lưu với deadline quá khứ, validation nên ở serializer
    assert job.deadline < timezone.now().date()


# ==========================================
# MODEL TESTS - SavedJob
# ==========================================

@pytest.mark.django_db
def test_saved_job_creation(candidate_user, job):
    """Test lưu job thành công"""
    saved_job = SavedJob.objects.create(
        user=candidate_user,
        job=job
    )
    
    assert saved_job.user == candidate_user
    assert saved_job.job == job
    assert saved_job.saved_at is not None


@pytest.mark.django_db
def test_saved_job_unique_constraint(candidate_user, job):
    """Test không thể lưu job trùng lặp"""
    SavedJob.objects.create(user=candidate_user, job=job)
    
    # Tạo lần 2 sẽ raise IntegrityError
    with pytest.raises(Exception):  # IntegrityError
        SavedJob.objects.create(user=candidate_user, job=job)


@pytest.mark.django_db
def test_saved_job_str_representation(candidate_user, job):
    """Test __str__ method"""
    saved_job = SavedJob.objects.create(user=candidate_user, job=job)
    expected = f"{candidate_user.email} saved {job.title}"
    assert str(saved_job) == expected


# ==========================================
# API TESTS - Job List & Detail
# ==========================================

@pytest.mark.django_db
def test_job_list_public_access(api_client, job):
    """Test danh sách job công khai"""
    url = reverse('job-list')
    response = api_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) >= 1


@pytest.mark.django_db
def test_job_list_filter_by_location(api_client, company):
    """Test lọc job theo location"""
    Job.objects.create(
        title='Hanoi Job',
        company=company,
        location='Hà Nội',
        job_type='FULL_TIME',
        description='Test',
        requirements='Test',
        deadline=timezone.now().date() + timedelta(days=30),
        status='PUBLISHED'
    )
    
    Job.objects.create(
        title='HCMC Job',
        company=company,
        location='Hồ Chí Minh',
        job_type='FULL_TIME',
        description='Test',
        requirements='Test',
        deadline=timezone.now().date() + timedelta(days=30),
        status='PUBLISHED'
    )
    
    url = reverse('job-list')
    response = api_client.get(url, {'location': 'Hà Nội'})
    
    assert response.status_code == status.HTTP_200_OK
    # Kiểm tra kết quả có lọc đúng
    for job in response.data['results']:
        assert 'Hà Nội' in job['location']


@pytest.mark.django_db
def test_job_detail_public_access(api_client, job):
    """Test xem chi tiết job"""
    url = reverse('job-detail', kwargs={'slug': job.slug})
    response = api_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['title'] == job.title
    assert response.data['company']['name'] == job.company.name


@pytest.mark.django_db
def test_job_detail_increments_views(api_client, job):
    """Test views_count tăng khi xem job"""
    url = reverse('job-detail', kwargs={'slug': job.slug})
    initial_views = job.views_count
    
    api_client.get(url)
    
    job.refresh_from_db()
    assert job.views_count == initial_views + 1


@pytest.mark.django_db
def test_job_search_by_title(api_client, company):
    """Test tìm kiếm job theo title"""
    Job.objects.create(
        title='Senior Python Developer',
        company=company,
        location='Hà Nội',
        job_type='FULL_TIME',
        description='Test',
        requirements='Test',
        deadline=timezone.now().date() + timedelta(days=30),
        status='PUBLISHED'
    )
    
    url = reverse('job-list')
    response = api_client.get(url, {'search': 'Python'})
    
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) >= 1


# ==========================================
# API TESTS - Job Creation & Update (Recruiter)
# ==========================================

@pytest.mark.django_db
def test_create_job_as_recruiter(api_client, recruiter_user, company):
    """Test recruiter tạo job"""
    api_client.force_authenticate(user=recruiter_user)
    
    url = reverse('job-list')
    data = {
        'title': 'New Job Position',
        'company': company.id,
        'location': 'Đà Nẵng',
        'job_type': 'FULL_TIME',
        'description': 'Job description',
        'requirements': 'Job requirements',
        'benefits': 'Job benefits',
        'deadline': (timezone.now().date() + timedelta(days=30)).isoformat(),
    }
    
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_201_CREATED
    assert Job.objects.filter(title='New Job Position').exists()


@pytest.mark.django_db
def test_create_job_as_candidate_forbidden(api_client, candidate_user, company):
    """Test candidate không thể tạo job"""
    api_client.force_authenticate(user=candidate_user)
    
    url = reverse('job-list')
    data = {
        'title': 'Unauthorized Job',
        'company': company.id,
        'location': 'Test',
        'job_type': 'FULL_TIME',
        'description': 'Test',
        'requirements': 'Test',
        'deadline': (timezone.now().date() + timedelta(days=30)).isoformat(),
    }
    
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_update_job_as_owner(api_client, recruiter_user, job):
    """Test recruiter cập nhật job của mình"""
    api_client.force_authenticate(user=recruiter_user)
    
    url = reverse('job-detail', kwargs={'slug': job.slug})
    data = {
        'title': 'Updated Job Title',
        'description': 'Updated description'
    }
    
    response = api_client.patch(url, data, format='json')
    
    assert response.status_code == status.HTTP_200_OK
    
    job.refresh_from_db()
    assert job.title == 'Updated Job Title'


@pytest.mark.django_db
def test_delete_job_as_owner(api_client, recruiter_user, job):
    """Test recruiter xóa job của mình"""
    api_client.force_authenticate(user=recruiter_user)
    
    url = reverse('job-detail', kwargs={'slug': job.slug})
    response = api_client.delete(url)
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Job.objects.filter(id=job.id).exists()


# ==========================================
# API TESTS - SavedJob
# ==========================================

@pytest.mark.django_db
def test_save_job_as_candidate(api_client, candidate_user, job):
    """Test candidate lưu job"""
    api_client.force_authenticate(user=candidate_user)
    
    url = reverse('job-save', kwargs={'slug': job.slug})
    response = api_client.post(url)
    
    assert response.status_code == status.HTTP_201_CREATED
    assert SavedJob.objects.filter(user=candidate_user, job=job).exists()


@pytest.mark.django_db
def test_unsave_job(api_client, candidate_user, job):
    """Test bỏ lưu job"""
    api_client.force_authenticate(user=candidate_user)
    
    # Lưu job trước
    SavedJob.objects.create(user=candidate_user, job=job)
    
    url = reverse('job-unsave', kwargs={'slug': job.slug})
    response = api_client.delete(url)
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not SavedJob.objects.filter(user=candidate_user, job=job).exists()


@pytest.mark.django_db
def test_list_saved_jobs(api_client, candidate_user, job):
    """Test xem danh sách job đã lưu"""
    api_client.force_authenticate(user=candidate_user)
    
    SavedJob.objects.create(user=candidate_user, job=job)
    
    url = reverse('saved-jobs-list')
    response = api_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert len(response.data['results']) >= 1


@pytest.mark.django_db
def test_save_job_requires_authentication(api_client, job):
    """Test lưu job yêu cầu đăng nhập"""
    url = reverse('job-save', kwargs={'slug': job.slug})
    response = api_client.post(url)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==========================================
# EDGE CASES & VALIDATION
# ==========================================

@pytest.mark.django_db
def test_create_job_with_past_deadline(api_client, recruiter_user, company):
    """Test tạo job với deadline quá khứ bị reject"""
    api_client.force_authenticate(user=recruiter_user)
    
    url = reverse('job-list')
    data = {
        'title': 'Invalid Job',
        'company': company.id,
        'location': 'Test',
        'job_type': 'FULL_TIME',
        'description': 'Test',
        'requirements': 'Test',
        'deadline': (timezone.now().date() - timedelta(days=1)).isoformat(),
    }
    
    response = api_client.post(url, data, format='json')
    
    # Serializer validation nên reject
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_create_job_missing_required_fields(api_client, recruiter_user):
    """Test tạo job thiếu trường bắt buộc"""
    api_client.force_authenticate(user=recruiter_user)
    
    url = reverse('job-list')
    data = {
        'title': 'Incomplete Job'
        # Thiếu company, location, etc.
    }
    
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_job_status_draft_not_public(api_client, company):
    """Test job DRAFT không hiển thị public"""
    draft_job = Job.objects.create(
        title='Draft Job',
        company=company,
        location='Test',
        job_type='FULL_TIME',
        description='Test',
        requirements='Test',
        deadline=timezone.now().date() + timedelta(days=30),
        status='DRAFT'
    )
    
    url = reverse('job-list')
    response = api_client.get(url)
    
    # DRAFT jobs không nên xuất hiện trong list public
    job_ids = [job['id'] for job in response.data['results']]
    assert draft_job.id not in job_ids
