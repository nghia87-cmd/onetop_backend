from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse

from .models import Company

User = get_user_model()


class CompanyModelTest(TestCase):
    """Test cho Company Model"""

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
            description='A leading tech company',
            address='123 Test Street, Hanoi',
            website='https://testcompany.com',
            employee_count='50-100',
            owner=self.recruiter
        )

    def test_company_creation(self):
        """Test tạo company thành công"""
        self.assertEqual(self.company.name, 'Test Company')
        self.assertEqual(self.company.owner, self.recruiter)

    def test_company_str_representation(self):
        """Test __str__ method"""
        self.assertEqual(str(self.company), 'Test Company')

    def test_company_slug_generation(self):
        """Test slug được tạo tự động"""
        self.assertIsNotNone(self.company.slug)
        self.assertEqual(self.company.slug, 'test-company')

    def test_company_unique_name(self):
        """Test tên công ty phải unique"""
        with self.assertRaises(Exception):
            Company.objects.create(
                name='Test Company',  # Trùng tên
                description='Another company',
                address='Test Address',
                owner=self.recruiter
            )

    def test_company_verbose_name_plural(self):
        """Test verbose name plural"""
        self.assertEqual(str(Company._meta.verbose_name_plural), 'Companies')


class CompanyAPITest(APITestCase):
    """Test cho Company API"""

    def setUp(self):
        self.client = APIClient()
        
        self.recruiter = User.objects.create_user(
            email='recruiter@test.com',
            username='recruiter@test.com',
            password='testpass123',
            full_name='Test Recruiter',
            user_type='RECRUITER'
        )
        
        self.other_recruiter = User.objects.create_user(
            email='other@test.com',
            username='other@test.com',
            password='testpass123',
            full_name='Other Recruiter',
            user_type='RECRUITER'
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
        
        self.companies_url = reverse('v1:company-list')

    def test_list_companies_public(self):
        """Test danh sách công ty công khai"""
        response = self.client.get(self.companies_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data['results']) > 0)

    def test_create_company_success(self):
        """Test recruiter tạo công ty thành công"""
        self.client.force_authenticate(user=self.recruiter)
        
        data = {
            'name': 'New Company',
            'description': 'New company description',
            'address': 'New Address',
            'website': 'https://newcompany.com',
            'employee_count': '10-50'
        }
        
        response = self.client.post(self.companies_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Company.objects.filter(name='New Company').exists())
        
        # Kiểm tra owner được set đúng
        company = Company.objects.get(name='New Company')
        self.assertEqual(company.owner, self.recruiter)

    def test_candidate_cannot_create_company(self):
        """Test candidate không thể tạo công ty"""
        self.client.force_authenticate(user=self.candidate)
        
        data = {
            'name': 'Candidate Company',
            'description': 'Description',
            'address': 'Address'
        }
        
        response = self.client.post(self.companies_url, data, format='json')
        
        # Tùy logic API, có thể là 403 hoặc không cho phép
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST])

    def test_update_own_company(self):
        """Test recruiter cập nhật công ty của mình"""
        self.client.force_authenticate(user=self.recruiter)
        
        url = reverse('v1:company-detail', args=[self.company.id])
        data = {
            'description': 'Updated description'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.company.refresh_from_db()
        self.assertEqual(self.company.description, 'Updated description')

    def test_cannot_update_other_company(self):
        """Test không thể cập nhật công ty của người khác"""
        self.client.force_authenticate(user=self.other_recruiter)
        
        url = reverse('v1:company-detail', args=[self.company.id])
        data = {
            'description': 'Unauthorized update'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_own_company(self):
        """Test xóa công ty của mình"""
        self.client.force_authenticate(user=self.recruiter)
        
        url = reverse('v1:company-detail', args=[self.company.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Company.objects.filter(id=self.company.id).exists())

    def test_cannot_delete_other_company(self):
        """Test không thể xóa công ty của người khác"""
        self.client.force_authenticate(user=self.other_recruiter)
        
        url = reverse('v1:company-detail', args=[self.company.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_company_detail(self):
        """Test xem chi tiết công ty"""
        url = reverse('v1:company-detail', args=[self.company.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Company')
