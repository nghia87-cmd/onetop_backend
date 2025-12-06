"""
Pytest-style tests cho Companies app
Ví dụ refactor để sử dụng fixtures từ conftest.py
"""
import pytest
from rest_framework import status
from django.urls import reverse

from apps.companies.models import Company


# ==========================================
# MODEL TESTS - Sử dụng fixtures
# ==========================================

@pytest.mark.django_db
def test_company_creation(recruiter_user):
    """Test tạo company thành công"""
    company = Company.objects.create(
        name='Test Company',
        description='A leading tech company',
        address='123 Test Street, Hanoi',
        owner=recruiter_user
    )
    
    assert company.name == 'Test Company'
    assert company.owner == recruiter_user
    assert str(company) == 'Test Company'


@pytest.mark.django_db
def test_company_slug_generation(recruiter_user):
    """Test slug được tạo tự động"""
    company = Company.objects.create(
        name='My Test Company',
        description='Description',
        address='Address',
        owner=recruiter_user
    )
    
    assert company.slug is not None
    assert company.slug == 'my-test-company'


@pytest.mark.django_db
def test_company_unique_name(recruiter_user):
    """Test tên công ty phải unique"""
    Company.objects.create(
        name='Unique Company',
        description='First',
        address='Address',
        owner=recruiter_user
    )
    
    # Tạo company trùng tên sẽ raise exception
    with pytest.raises(Exception):
        Company.objects.create(
            name='Unique Company',
            description='Second',
            address='Address',
            owner=recruiter_user
        )


# ==========================================
# API TESTS - Sử dụng authenticated_client
# ==========================================

@pytest.mark.django_db
def test_list_companies_public(api_client):
    """Test danh sách công ty công khai"""
    url = reverse('company-list')
    response = api_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_create_company_success(authenticated_client, recruiter_user, company):
    """Test recruiter tạo công ty thành công"""
    url = reverse('company-list')
    data = {
        'name': 'New Company',
        'description': 'New company description',
        'address': 'New Address',
        'website': 'https://newcompany.com',
        'employee_count': '10-50'
    }
    
    response = authenticated_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_201_CREATED
    assert Company.objects.filter(name='New Company').exists()
    
    # Kiểm tra owner được set đúng
    new_company = Company.objects.get(name='New Company')
    assert new_company.owner == recruiter_user


@pytest.mark.django_db
def test_candidate_cannot_create_company(candidate_client):
    """Test candidate không thể tạo công ty"""
    url = reverse('company-list')
    data = {
        'name': 'Candidate Company',
        'description': 'Description',
        'address': 'Address'
    }
    
    response = candidate_client.post(url, data, format='json')
    
    # Expect 403 Forbidden
    assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]


@pytest.mark.django_db
def test_update_own_company(authenticated_client, company):
    """Test recruiter cập nhật công ty của mình"""
    url = reverse('company-detail', args=[company.id])
    data = {
        'description': 'Updated description'
    }
    
    response = authenticated_client.patch(url, data, format='json')
    
    assert response.status_code == status.HTTP_200_OK
    
    company.refresh_from_db()
    assert company.description == 'Updated description'


@pytest.mark.django_db
def test_cannot_update_other_company(api_client, company):
    """Test không thể cập nhật công ty của người khác"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Tạo recruiter khác
    other_recruiter = User.objects.create_user(
        email='other@test.com',
        username='other@test.com',
        password='testpass123',
        full_name='Other Recruiter',
        user_type='RECRUITER'
    )
    
    api_client.force_authenticate(user=other_recruiter)
    
    url = reverse('company-detail', args=[company.id])
    data = {
        'description': 'Unauthorized update'
    }
    
    response = api_client.patch(url, data, format='json')
    
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_delete_own_company(authenticated_client, company):
    """Test xóa công ty của mình"""
    url = reverse('company-detail', args=[company.id])
    response = authenticated_client.delete(url)
    
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Company.objects.filter(id=company.id).exists()


@pytest.mark.django_db
def test_get_company_detail(api_client, company):
    """Test xem chi tiết công ty"""
    url = reverse('company-detail', args=[company.id])
    response = api_client.get(url)
    
    assert response.status_code == status.HTTP_200_OK
    assert response.data['name'] == company.name


# ==========================================
# PARAMETERIZED TESTS - Tính năng mạnh của pytest
# ==========================================

@pytest.mark.django_db
@pytest.mark.parametrize("employee_count,expected", [
    ("1-10", True),
    ("10-50", True),
    ("50-100", True),
    ("100-500", True),
    ("500+", True),
])
def test_company_employee_count_options(recruiter_user, employee_count, expected):
    """Test các options employee_count hợp lệ"""
    company = Company.objects.create(
        name=f'Company {employee_count}',
        description='Test',
        address='Test',
        owner=recruiter_user,
        employee_count=employee_count
    )
    
    assert (company.employee_count == employee_count) == expected
