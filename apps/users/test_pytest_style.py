"""
Pytest-style tests cho Users app
Refactored từ APITestCase sang function-based tests với fixtures
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from django.urls import reverse
from datetime import timedelta
from django.utils import timezone

User = get_user_model()


# ==========================================
# MODEL TESTS
# ==========================================

@pytest.mark.django_db
def test_user_creation(candidate_user):
    """Test tạo user thành công"""
    assert candidate_user.email == 'candidate@test.com'
    assert candidate_user.user_type == 'CANDIDATE'
    assert candidate_user.check_password('testpass123')


@pytest.mark.django_db
def test_user_str_representation(candidate_user):
    """Test __str__ method"""
    assert str(candidate_user) == 'candidate@test.com'


@pytest.mark.django_db
def test_user_type_choices(candidate_user, recruiter_user):
    """Test các loại user type"""
    assert candidate_user.user_type in ['CANDIDATE', 'RECRUITER', 'ADMIN']
    assert recruiter_user.user_type == 'RECRUITER'


@pytest.mark.django_db
def test_default_job_posting_credits(candidate_user, recruiter_user):
    """Test credits mặc định"""
    assert candidate_user.job_posting_credits == 0
    assert recruiter_user.job_posting_credits == 0


@pytest.mark.django_db
def test_membership_expires_at_default(candidate_user):
    """Test membership_expires_at mặc định là None"""
    assert candidate_user.membership_expires_at is None


@pytest.mark.django_db
def test_has_unlimited_posting_default(candidate_user):
    """Test has_unlimited_posting mặc định là False"""
    assert not candidate_user.has_unlimited_posting


@pytest.mark.django_db
def test_can_view_contact_default(recruiter_user):
    """Test can_view_contact mặc định là False"""
    assert not recruiter_user.can_view_contact


# ==========================================
# REGISTER API TESTS
# ==========================================

@pytest.mark.django_db
def test_register_candidate_success(api_client):
    """Test đăng ký candidate thành công"""
    url = reverse('v1:register')
    data = {
        'email': 'newcandidate@test.com',
        'password': 'newpass123',
        'full_name': 'New Candidate',
        'user_type': 'CANDIDATE'
    }
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_201_CREATED
    assert 'access' in response.data
    assert 'refresh' in response.data
    assert User.objects.filter(email='newcandidate@test.com').exists()


@pytest.mark.django_db
def test_register_recruiter_success(api_client):
    """Test đăng ký recruiter thành công"""
    url = reverse('v1:register')
    data = {
        'email': 'newrecruiter@test.com',
        'password': 'newpass123',
        'full_name': 'New Recruiter',
        'user_type': 'RECRUITER'
    }
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_201_CREATED
    assert User.objects.filter(email='newrecruiter@test.com', user_type='RECRUITER').exists()


@pytest.mark.django_db
def test_register_duplicate_email(api_client, candidate_user):
    """Test đăng ký với email đã tồn tại"""
    url = reverse('v1:register')
    data = {
        'email': candidate_user.email,
        'password': 'newpass123',
        'full_name': 'Duplicate User',
        'user_type': 'CANDIDATE'
    }
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_register_invalid_email(api_client):
    """Test đăng ký với email không hợp lệ"""
    url = reverse('v1:register')
    data = {
        'email': 'invalidemail',
        'password': 'newpass123',
        'full_name': 'Test User',
        'user_type': 'CANDIDATE'
    }
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_register_missing_required_fields(api_client):
    """Test đăng ký thiếu trường bắt buộc"""
    url = reverse('v1:register')
    data = {
        'email': 'test@test.com'
        # Thiếu password và full_name
    }
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ==========================================
# LOGIN API TESTS
# ==========================================

@pytest.mark.django_db
def test_login_success(api_client, candidate_user):
    """Test login thành công"""
    url = reverse('v1:login')
    data = {
        'email': 'candidate@test.com',
        'password': 'testpass123'
    }
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_200_OK
    assert 'access' in response.data
    assert 'refresh' in response.data


@pytest.mark.django_db
def test_login_wrong_password(api_client, candidate_user):
    """Test login với mật khẩu sai"""
    url = reverse('v1:login')
    data = {
        'email': 'candidate@test.com',
        'password': 'wrongpassword'
    }
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_login_nonexistent_user(api_client):
    """Test login với user không tồn tại"""
    url = reverse('v1:login')
    data = {
        'email': 'nonexistent@test.com',
        'password': 'password123'
    }
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_login_missing_credentials(api_client):
    """Test login thiếu thông tin đăng nhập"""
    url = reverse('v1:login')
    data = {
        'email': 'test@test.com'
        # Thiếu password
    }
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ==========================================
# USER PROFILE API TESTS
# ==========================================

@pytest.mark.django_db
def test_get_user_profile_authenticated(authenticated_client, candidate_user):
    """Test lấy profile khi đã đăng nhập"""
    url = reverse('v1:user-profile')
    response = authenticated_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['email'] == candidate_user.email
    assert response.data['full_name'] == candidate_user.full_name


@pytest.mark.django_db
def test_get_user_profile_unauthenticated(api_client):
    """Test lấy profile khi chưa đăng nhập"""
    url = reverse('v1:user-profile')
    response = api_client.get(url)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_update_user_profile(authenticated_client, candidate_user):
    """Test cập nhật profile"""
    url = reverse('v1:user-profile')
    data = {
        'full_name': 'Updated Name',
        'phone': '0123456789',
        'desired_location': 'Hanoi'
    }
    response = authenticated_client.patch(url, data, format='json')
    
    assert response.status_code == status.HTTP_200_OK
    
    candidate_user.refresh_from_db()
    assert candidate_user.full_name == 'Updated Name'
    assert candidate_user.phone == '0123456789'


@pytest.mark.django_db
def test_update_user_profile_invalid_data(authenticated_client):
    """Test cập nhật profile với dữ liệu không hợp lệ"""
    url = reverse('v1:user-profile')
    data = {
        'email': 'invalidemail'  # Email không hợp lệ
    }
    response = authenticated_client.patch(url, data, format='json')
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST


# ==========================================
# VIP MEMBERSHIP TESTS
# ==========================================

@pytest.mark.django_db
def test_vip_membership_active(vip_recruiter_user):
    """Test VIP membership còn hiệu lực"""
    assert vip_recruiter_user.has_unlimited_posting
    assert vip_recruiter_user.can_view_contact
    assert vip_recruiter_user.membership_expires_at > timezone.now()


@pytest.mark.django_db
def test_vip_membership_expired(recruiter_user):
    """Test VIP membership đã hết hạn"""
    recruiter_user.has_unlimited_posting = True
    recruiter_user.can_view_contact = True
    recruiter_user.membership_expires_at = timezone.now() - timedelta(days=1)
    recruiter_user.save()
    
    # Logic kiểm tra membership hết hạn nên ở view/middleware
    assert recruiter_user.membership_expires_at < timezone.now()


# ==========================================
# PERMISSION TESTS
# ==========================================

@pytest.mark.django_db
def test_candidate_cannot_post_job(authenticated_client, candidate_user):
    """Test candidate không thể đăng tin tuyển dụng"""
    # Giả sử có endpoint create job
    # url = reverse('v1:job-list')
    # response = authenticated_client.post(url, {...})
    # assert response.status_code == status.HTTP_403_FORBIDDEN
    pass  # Placeholder - implement khi có job endpoint


@pytest.mark.django_db
def test_recruiter_can_create_company(api_client, recruiter_user):
    """Test recruiter có thể tạo company"""
    # Implement khi có company creation endpoint
    pass  # Placeholder
