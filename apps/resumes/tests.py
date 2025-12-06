from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta

from .models import Resume, WorkExperience, Education, Skill

User = get_user_model()


class ResumeModelTest(TestCase):
    """Test cho Resume Model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            username='user@test.com',
            password='testpass123',
            full_name='Test User',
            user_type='CANDIDATE'
        )
        
        self.resume = Resume.objects.create(
            user=self.user,
            title='My CV',
            full_name='Test User',
            email='user@test.com',
            phone='0123456789',
            address='Hanoi',
            summary='Experienced developer',
            is_primary=True
        )

    def test_resume_creation(self):
        """Test tạo resume thành công"""
        self.assertEqual(self.resume.user, self.user)
        self.assertEqual(self.resume.title, 'My CV')
        self.assertTrue(self.resume.is_primary)

    def test_resume_str_representation(self):
        """Test __str__ method"""
        expected = f"{self.resume.title} - {self.user.email}"
        self.assertEqual(str(self.resume), expected)

    def test_resume_default_title(self):
        """Test title mặc định"""
        resume = Resume.objects.create(
            user=self.user,
            full_name='Test User',
            email='user@test.com',
            phone='0123456789'
        )
        self.assertEqual(resume.title, 'CV chưa đặt tên')

    def test_resume_with_file(self):
        """Test resume có file đính kèm"""
        cv_file = SimpleUploadedFile(
            "cv.pdf",
            b"PDF content",
            content_type="application/pdf"
        )
        
        resume = Resume.objects.create(
            user=self.user,
            title='CV with file',
            full_name='Test User',
            email='user@test.com',
            phone='0123456789',
            file=cv_file
        )
        
        self.assertIsNotNone(resume.file)

    def test_multiple_resumes_per_user(self):
        """Test user có thể có nhiều CV"""
        Resume.objects.create(
            user=self.user,
            title='Second CV',
            full_name='Test User',
            email='user@test.com',
            phone='0123456789'
        )
        
        self.assertEqual(Resume.objects.filter(user=self.user).count(), 2)

    def test_only_one_primary_resume(self):
        """Test chỉ có 1 CV primary - Auto unset via signal"""
        # Resume ban đầu đã là primary
        self.assertTrue(self.resume.is_primary)
        
        # Tạo resume thứ 2 và set primary
        resume2 = Resume.objects.create(
            user=self.user,
            title='Second CV',
            full_name='Test User',
            email='user@test.com',
            phone='0123456789',
            is_primary=True
        )
        
        # Resume 2 phải là primary
        self.assertTrue(resume2.is_primary)
        
        # Resume 1 tự động unset primary (qua signal)
        self.resume.refresh_from_db()
        self.assertFalse(self.resume.is_primary)
        
        # Verify chỉ có 1 primary resume
        primary_count = Resume.objects.filter(user=self.user, is_primary=True).count()
        self.assertEqual(primary_count, 1)


class WorkExperienceModelTest(TestCase):
    """Test cho WorkExperience Model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            username='user@test.com',
            password='testpass123',
            full_name='Test User',
            user_type='CANDIDATE'
        )
        
        self.resume = Resume.objects.create(
            user=self.user,
            title='My CV',
            full_name='Test User',
            email='user@test.com',
            phone='0123456789'
        )
        
        self.experience = WorkExperience.objects.create(
            resume=self.resume,
            company_name='ABC Company',
            position='Python Developer',
            start_date=date(2020, 1, 1),
            end_date=date(2022, 12, 31),
            description='Developed web applications'
        )

    def test_work_experience_creation(self):
        """Test tạo work experience thành công"""
        self.assertEqual(self.experience.resume, self.resume)
        self.assertEqual(self.experience.company_name, 'ABC Company')
        self.assertEqual(self.experience.position, 'Python Developer')

    def test_current_job_no_end_date(self):
        """Test công việc hiện tại không có end_date"""
        current_job = WorkExperience.objects.create(
            resume=self.resume,
            company_name='Current Company',
            position='Senior Developer',
            start_date=date(2023, 1, 1),
            is_current=True
        )
        
        self.assertTrue(current_job.is_current)
        self.assertIsNone(current_job.end_date)

    def test_work_experience_ordering(self):
        """Test experiences được sắp xếp theo start_date giảm dần"""
        old_exp = WorkExperience.objects.create(
            resume=self.resume,
            company_name='Old Company',
            position='Junior Dev',
            start_date=date(2018, 1, 1),
            end_date=date(2019, 12, 31)
        )
        
        experiences = WorkExperience.objects.filter(resume=self.resume)
        self.assertEqual(experiences[0], self.experience)  # 2020
        self.assertEqual(experiences[1], old_exp)  # 2018


class EducationModelTest(TestCase):
    """Test cho Education Model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            username='user@test.com',
            password='testpass123',
            full_name='Test User',
            user_type='CANDIDATE'
        )
        
        self.resume = Resume.objects.create(
            user=self.user,
            title='My CV',
            full_name='Test User',
            email='user@test.com',
            phone='0123456789'
        )
        
        self.education = Education.objects.create(
            resume=self.resume,
            school_name='ABC University',
            major='Computer Science',
            degree='Bachelor',
            start_date=date(2016, 9, 1),
            end_date=date(2020, 6, 30)
        )

    def test_education_creation(self):
        """Test tạo education thành công"""
        self.assertEqual(self.education.resume, self.resume)
        self.assertEqual(self.education.school_name, 'ABC University')
        self.assertEqual(self.education.major, 'Computer Science')

    def test_education_ordering(self):
        """Test education được sắp xếp theo start_date giảm dần"""
        master = Education.objects.create(
            resume=self.resume,
            school_name='XYZ University',
            major='Software Engineering',
            degree='Master',
            start_date=date(2020, 9, 1),
            end_date=date(2022, 6, 30)
        )
        
        educations = Education.objects.filter(resume=self.resume)
        self.assertEqual(educations[0], master)  # 2020
        self.assertEqual(educations[1], self.education)  # 2016


class SkillModelTest(TestCase):
    """Test cho Skill Model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            username='user@test.com',
            password='testpass123',
            full_name='Test User',
            user_type='CANDIDATE'
        )
        
        self.resume = Resume.objects.create(
            user=self.user,
            title='My CV',
            full_name='Test User',
            email='user@test.com',
            phone='0123456789'
        )
        
        self.skill = Skill.objects.create(
            resume=self.resume,
            name='Python',
            level=4
        )

    def test_skill_creation(self):
        """Test tạo skill thành công"""
        self.assertEqual(self.skill.resume, self.resume)
        self.assertEqual(self.skill.name, 'Python')
        self.assertEqual(self.skill.level, 4)

    def test_skill_default_level(self):
        """Test skill level mặc định là 1"""
        skill = Skill.objects.create(
            resume=self.resume,
            name='JavaScript'
        )
        self.assertEqual(skill.level, 1)

    def test_multiple_skills(self):
        """Test resume có nhiều skills"""
        Skill.objects.create(resume=self.resume, name='Django', level=5)
        Skill.objects.create(resume=self.resume, name='React', level=3)
        
        self.assertEqual(Skill.objects.filter(resume=self.resume).count(), 3)


class ResumeAPITest(APITestCase):
    """Test cho Resume API"""

    def setUp(self):
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            email='user@test.com',
            username='user@test.com',
            password='testpass123',
            full_name='Test User',
            user_type='CANDIDATE'
        )
        
        self.other_user = User.objects.create_user(
            email='other@test.com',
            username='other@test.com',
            password='testpass123',
            full_name='Other User',
            user_type='CANDIDATE'
        )
        
        self.resume = Resume.objects.create(
            user=self.user,
            title='My CV',
            full_name='Test User',
            email='user@test.com',
            phone='0123456789'
        )
        
        self.resumes_url = reverse('resume-list')

    def test_list_own_resumes(self):
        """Test user chỉ xem được CV của mình"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.resumes_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_cannot_see_other_resumes(self):
        """Test không thể xem CV của người khác"""
        self.client.force_authenticate(user=self.other_user)
        
        response = self.client.get(self.resumes_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_create_resume(self):
        """Test tạo CV mới"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'title': 'New CV',
            'full_name': 'Test User',
            'email': 'user@test.com',
            'phone': '0987654321',
            'summary': 'Experienced in Python'
        }
        
        response = self.client.post(self.resumes_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Resume.objects.filter(user=self.user).count(), 2)

    def test_update_resume(self):
        """Test cập nhật CV"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('resume-detail', args=[self.resume.id])
        data = {
            'summary': 'Updated summary'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.resume.refresh_from_db()
        self.assertEqual(self.resume.summary, 'Updated summary')

    def test_delete_resume(self):
        """Test xóa CV"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('resume-detail', args=[self.resume.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Resume.objects.filter(id=self.resume.id).exists())

    def test_cannot_update_other_resume(self):
        """Test không thể cập nhật CV của người khác"""
        self.client.force_authenticate(user=self.other_user)
        
        url = reverse('resume-detail', args=[self.resume.id])
        data = {
            'summary': 'Hacked summary'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_generate_pdf(self):
        """Test trigger tạo PDF với Mock"""
        from unittest.mock import patch, MagicMock
        
        self.client.force_authenticate(user=self.user)
        
        with patch('apps.resumes.tasks.HTML') as mock_html_class:
            # Setup mock WeasyPrint
            mock_html_instance = MagicMock()
            mock_html_class.return_value = mock_html_instance
            mock_html_instance.write_pdf.return_value = b'%PDF-1.4\nFake PDF content'
            
            url = reverse('resume-generate-pdf', args=[self.resume.id])
            response = self.client.post(url)
            
            # Expect 200 hoặc 202 (processing)
            self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_202_ACCEPTED])


class ResumePDFGenerationTest(TestCase):
    """Test cho PDF generation với Mocking"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            username='user@test.com',
            password='testpass123',
            full_name='Test User',
            user_type='CANDIDATE'
        )
        
        self.resume = Resume.objects.create(
            user=self.user,
            title='My CV',
            full_name='Test User',
            email='user@test.com',
            phone='0123456789',
            summary='Experienced developer'
        )
        
        # Add some data
        WorkExperience.objects.create(
            resume=self.resume,
            company_name='ABC Corp',
            position='Developer',
            start_date=date(2020, 1, 1),
            end_date=date(2022, 12, 31),
            description='Worked on web apps'
        )
        
        Education.objects.create(
            resume=self.resume,
            school_name='University',
            major='Computer Science',
            degree='Bachelor',
            start_date=date(2016, 9, 1),
            end_date=date(2020, 6, 30)
        )
        
        Skill.objects.create(resume=self.resume, name='Python', level=5)
        Skill.objects.create(resume=self.resume, name='Django', level=4)

    def test_pdf_generation_task_with_mock(self):
        """Test Celery task tạo PDF với Mock WeasyPrint"""
        from unittest.mock import patch, MagicMock, mock_open
        from apps.resumes.tasks import generate_resume_pdf_async
        
        with patch('apps.resumes.tasks.HTML') as mock_html_class:
            # Mock HTML class
            mock_html_instance = MagicMock()
            mock_html_class.return_value = mock_html_instance
            
            # Mock write_pdf method
            fake_pdf_bytes = b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\nFake PDF content'
            mock_html_instance.write_pdf.return_value = fake_pdf_bytes
            
            # Mock file operations
            with patch('builtins.open', mock_open()) as mock_file:
                # Call task
                result = generate_resume_pdf_async(self.resume.id)
                
                # Assert success message
                self.assertIn('generated and saved', result.lower())
                
                # Verify HTML was called with correct data
                mock_html_class.assert_called_once()
                
                # Verify write_pdf was called
                mock_html_instance.write_pdf.assert_called_once()

    def test_pdf_generation_handles_missing_resume(self):
        """Test task xử lý khi resume không tồn tại"""
        from apps.resumes.tasks import generate_resume_pdf_async
        
        result = generate_resume_pdf_async(99999)  # Non-existent ID
        
        self.assertIn('not found', result.lower())

    def test_pdf_file_saved_to_resume(self):
        """Test PDF file được lưu vào resume.pdf_file"""
        from unittest.mock import patch, MagicMock
        from django.core.files.base import ContentFile
        
        with patch('apps.resumes.tasks.HTML') as mock_html_class:
            mock_html_instance = MagicMock()
            mock_html_class.return_value = mock_html_instance
            
            fake_pdf_bytes = b'%PDF-1.4\nFake content'
            mock_html_instance.write_pdf.return_value = fake_pdf_bytes
            
            # Manually simulate task logic
            from apps.resumes.tasks import generate_resume_pdf_async
            
            with patch('apps.resumes.tasks.default_storage') as mock_storage:
                mock_storage.save.return_value = f'resumes/pdf_output/resume_{self.resume.id}.pdf'
                
                result = generate_resume_pdf_async(self.resume.id)
                
                # Verify storage.save was called
                self.assertTrue(mock_storage.save.called)

    def test_pdf_generation_template_rendering(self):
        """Test template được render đúng với dữ liệu CV"""
        from unittest.mock import patch, MagicMock
        from django.template.loader import render_to_string
        
        # Render template thật để test
        html_content = render_to_string('resumes/resume_pdf.html', {
            'resume': self.resume,
            'experiences': self.resume.experiences.all(),
            'educations': self.resume.educations.all(),
            'skills': self.resume.skills.all(),
        })
        
        # Assert các thông tin quan trọng có trong HTML
        self.assertIn('Test User', html_content)
        self.assertIn('ABC Corp', html_content)
        self.assertIn('Python', html_content)
        self.assertIn('University', html_content)

    def test_unauthenticated_cannot_access(self):
        """Test chưa đăng nhập không thể truy cập"""
        response = self.client.get(self.resumes_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ResumeComponentsAPITest(APITestCase):
    """Test cho Resume Components (Experience, Education, Skill) API"""

    def setUp(self):
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            email='user@test.com',
            username='user@test.com',
            password='testpass123',
            full_name='Test User',
            user_type='CANDIDATE'
        )
        
        self.resume = Resume.objects.create(
            user=self.user,
            title='My CV',
            full_name='Test User',
            email='user@test.com',
            phone='0123456789'
        )

    def test_add_work_experience(self):
        """Test thêm kinh nghiệm làm việc"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('workexperience-list')
        data = {
            'resume': self.resume.id,
            'company_name': 'Tech Company',
            'position': 'Developer',
            'start_date': '2020-01-01',
            'end_date': '2022-12-31',
            'description': 'Worked on web apps'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(WorkExperience.objects.filter(resume=self.resume).exists())

    def test_add_education(self):
        """Test thêm học vấn"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('education-list')
        data = {
            'resume': self.resume.id,
            'school_name': 'University',
            'major': 'CS',
            'degree': 'Bachelor',
            'start_date': '2016-09-01',
            'end_date': '2020-06-30'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Education.objects.filter(resume=self.resume).exists())

    def test_add_skill(self):
        """Test thêm kỹ năng"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('skill-list')
        data = {
            'resume': self.resume.id,
            'name': 'Python',
            'level': 5
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Skill.objects.filter(resume=self.resume, name='Python').exists())

    def test_update_work_experience(self):
        """Test cập nhật kinh nghiệm"""
        experience = WorkExperience.objects.create(
            resume=self.resume,
            company_name='Old Company',
            position='Junior Dev',
            start_date=date(2020, 1, 1)
        )
        
        self.client.force_authenticate(user=self.user)
        
        url = reverse('workexperience-detail', args=[experience.id])
        data = {
            'position': 'Senior Dev'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        experience.refresh_from_db()
        self.assertEqual(experience.position, 'Senior Dev')

    def test_delete_skill(self):
        """Test xóa skill"""
        skill = Skill.objects.create(
            resume=self.resume,
            name='Old Skill',
            level=3
        )
        
        self.client.force_authenticate(user=self.user)
        
        url = reverse('skill-detail', args=[skill.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Skill.objects.filter(id=skill.id).exists())
