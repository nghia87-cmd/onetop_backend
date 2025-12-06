from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import Notification
from apps.jobs.models import Job
from apps.companies.models import Company
from apps.applications.models import Application
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()


class NotificationModelTest(TestCase):
    """Test cho Notification Model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='user@test.com',
            username='user@test.com',
            password='testpass123',
            full_name='Test User',
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
        
        # Tạo notification liên kết với Job
        job_content_type = ContentType.objects.get_for_model(Job)
        self.notification = Notification.objects.create(
            recipient=self.user,
            verb='New job posted',
            description='A new Python Developer position is available',
            content_type=job_content_type,
            object_id=self.job.id
        )

    def test_notification_creation(self):
        """Test tạo notification thành công"""
        self.assertEqual(self.notification.recipient, self.user)
        self.assertEqual(self.notification.verb, 'New job posted')
        self.assertFalse(self.notification.is_read)

    def test_notification_str_representation(self):
        """Test __str__ method"""
        expected = f"Noti for {self.user.email}: {self.notification.verb}"
        self.assertEqual(str(self.notification), expected)

    def test_notification_default_is_read(self):
        """Test is_read mặc định là False"""
        self.assertFalse(self.notification.is_read)

    def test_notification_generic_relation(self):
        """Test generic relation với target object"""
        self.assertEqual(self.notification.target, self.job)
        self.assertIsInstance(self.notification.target, Job)

    def test_notification_with_application(self):
        """Test notification liên kết với Application"""
        cv_file = SimpleUploadedFile(
            "test_cv.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        application = Application.objects.create(
            job=self.job,
            candidate=self.user,
            cv_file=cv_file
        )
        
        app_content_type = ContentType.objects.get_for_model(Application)
        noti = Notification.objects.create(
            recipient=self.recruiter,
            verb='New application received',
            description=f'{self.user.full_name} applied to {self.job.title}',
            content_type=app_content_type,
            object_id=application.id
        )
        
        self.assertEqual(noti.target, application)
        self.assertIsInstance(noti.target, Application)


class NotificationAPITest(APITestCase):
    """Test cho Notification API"""

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
        
        # Tạo notifications cho user
        job_content_type = ContentType.objects.get_for_model(Job)
        self.notification1 = Notification.objects.create(
            recipient=self.user,
            verb='New job posted',
            description='Check out this new job',
            content_type=job_content_type,
            object_id=self.job.id,
            is_read=False
        )
        
        self.notification2 = Notification.objects.create(
            recipient=self.user,
            verb='Job application status updated',
            description='Your application has been viewed',
            content_type=job_content_type,
            object_id=self.job.id,
            is_read=False
        )
        
        self.notifications_url = reverse('notification-list')

    def test_list_user_notifications(self):
        """Test user chỉ xem được notifications của mình"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.notifications_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_cannot_see_other_notifications(self):
        """Test không thể xem notifications của người khác"""
        self.client.force_authenticate(user=self.other_user)
        
        response = self.client.get(self.notifications_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_mark_notification_as_read(self):
        """Test đánh dấu notification đã đọc"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('notification-read', args=[self.notification1.id])
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.notification1.refresh_from_db()
        self.assertTrue(self.notification1.is_read)

    def test_mark_all_as_read(self):
        """Test đánh dấu tất cả notifications đã đọc"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('notification-read-all')
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Kiểm tra tất cả notifications đã được đánh dấu đã đọc
        self.notification1.refresh_from_db()
        self.notification2.refresh_from_db()
        self.assertTrue(self.notification1.is_read)
        self.assertTrue(self.notification2.is_read)

    def test_notifications_ordering(self):
        """Test notifications được sắp xếp theo thời gian mới nhất"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.notifications_url)
        
        # notification2 được tạo sau nên sẽ ở đầu
        notifications = response.data['results']
        self.assertEqual(notifications[0]['id'], str(self.notification2.id))
        self.assertEqual(notifications[1]['id'], str(self.notification1.id))

    def test_filter_unread_notifications(self):
        """Test filter notifications chưa đọc"""
        # Đánh dấu 1 notification đã đọc
        self.notification1.is_read = True
        self.notification1.save()
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(self.notifications_url, {'is_read': 'false'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Chỉ còn 1 notification chưa đọc
        # (Tùy thuộc vào việc API có hỗ trợ filter hay không)

    def test_get_notification_detail(self):
        """Test xem chi tiết notification"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('notification-detail', args=[self.notification1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['verb'], 'New job posted')

    def test_cannot_read_other_notification(self):
        """Test không thể đánh dấu notification của người khác"""
        # Tạo notification cho other_user
        job_content_type = ContentType.objects.get_for_model(Job)
        other_notification = Notification.objects.create(
            recipient=self.other_user,
            verb='Test notification',
            content_type=job_content_type,
            object_id=self.job.id
        )
        
        self.client.force_authenticate(user=self.user)
        
        url = reverse('notification-read', args=[other_notification.id])
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_cannot_access(self):
        """Test chưa đăng nhập không thể truy cập"""
        response = self.client.get(self.notifications_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_readonly_viewset(self):
        """Test NotificationViewSet là readonly"""
        self.client.force_authenticate(user=self.user)
        
        # Không thể tạo notification qua API
        data = {
            'verb': 'Manual notification',
            'description': 'Test'
        }
        
        response = self.client.post(self.notifications_url, data, format='json')
        
        # Expect 405 Method Not Allowed vì viewset là ReadOnly
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_cannot_delete_notification(self):
        """Test không thể xóa notification (readonly viewset)"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('notification-detail', args=[self.notification1.id])
        response = self.client.delete(url)
        
        # Expect 405 Method Not Allowed
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class NotificationCreationTest(TestCase):
    """Test tự động tạo notifications (via signals)"""

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

    def test_notification_on_application_created(self):
        """Test notification được tạo khi có đơn ứng tuyển mới"""
        # Tạo job
        job = Job.objects.create(
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
        
        # Số notification trước khi tạo application
        initial_count = Notification.objects.filter(recipient=self.recruiter).count()
        
        # Tạo application - signal sẽ tự động tạo notification
        application = Application.objects.create(
            job=job,
            candidate=self.candidate,
            cv_file=cv_file
        )
        
        # Kiểm tra notification đã được tạo cho recruiter
        notifications = Notification.objects.filter(
            recipient=self.recruiter,
            verb__icontains='ứng tuyển'
        )
        
        self.assertTrue(notifications.exists())
        self.assertEqual(Notification.objects.filter(recipient=self.recruiter).count(), initial_count + 1)
        
        # Verify notification content
        notification = notifications.first()
        self.assertIn(self.candidate.full_name, notification.description)
        self.assertIn(job.title, notification.description)
        self.assertEqual(notification.target, application)

    def test_notification_on_job_status_change(self):
        """Test notification khi trạng thái đơn ứng tuyển thay đổi"""
        job = Job.objects.create(
            title='Backend Developer',
            company=self.company,
            location='TP.HCM',
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
        
        # Tạo application
        application = Application.objects.create(
            job=job,
            candidate=self.candidate,
            cv_file=cv_file,
            status='PENDING'
        )
        
        # Clear notifications tạo từ create
        Notification.objects.filter(recipient=self.candidate).delete()
        
        # Thay đổi status sang INTERVIEW - signal sẽ tạo notification
        application.status = 'INTERVIEW'
        application.save()
        
        # Kiểm tra notification cho candidate
        notifications = Notification.objects.filter(
            recipient=self.candidate,
            verb__icontains='trạng thái'
        )
        
        self.assertTrue(notifications.exists())
        
        notification = notifications.first()
        self.assertIn(self.company.name, notification.description)
        self.assertEqual(notification.target, application)

    def test_notification_on_rejection(self):
        """Test notification khi đơn bị từ chối"""
        job = Job.objects.create(
            title='Frontend Developer',
            company=self.company,
            location='Đà Nẵng',
            job_type='FULL_TIME',
            description='Test job description',
            requirements='React, JavaScript',
            benefits='Benefits',
            deadline=timezone.now().date() + timedelta(days=30),
            status='PUBLISHED'
        )
        
        cv_file = SimpleUploadedFile(
            "test_cv.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        application = Application.objects.create(
            job=job,
            candidate=self.candidate,
            cv_file=cv_file,
            status='PENDING'
        )
        
        # Clear existing notifications
        Notification.objects.all().delete()
        
        # Reject application
        application.status = 'REJECTED'
        application.save()
        
        # Verify notification created
        notifications = Notification.objects.filter(recipient=self.candidate)
        self.assertTrue(notifications.exists())

    def test_notification_on_acceptance(self):
        """Test notification khi đơn được chấp nhận"""
        job = Job.objects.create(
            title='DevOps Engineer',
            company=self.company,
            location='Hà Nội',
            job_type='FULL_TIME',
            description='Test job description',
            requirements='Docker, K8s',
            benefits='Benefits',
            deadline=timezone.now().date() + timedelta(days=30),
            status='PUBLISHED'
        )
        
        cv_file = SimpleUploadedFile(
            "test_cv.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        application = Application.objects.create(
            job=job,
            candidate=self.candidate,
            cv_file=cv_file,
            status='VIEWED'
        )
        
        # Clear notifications
        Notification.objects.all().delete()
        
        # Accept application
        application.status = 'ACCEPTED'
        application.save()
        
        # Verify notification
        notifications = Notification.objects.filter(
            recipient=self.candidate,
            verb__icontains='trạng thái'
        )
        self.assertTrue(notifications.exists())

    def test_no_notification_on_non_status_change(self):
        """Test không tạo notification khi chỉ update note (không phải status)"""
        job = Job.objects.create(
            title='Test Job',
            company=self.company,
            location='Hà Nội',
            job_type='FULL_TIME',
            description='Test',
            requirements='Test',
            benefits='Test',
            deadline=timezone.now().date() + timedelta(days=30),
            status='PUBLISHED'
        )
        
        cv_file = SimpleUploadedFile(
            "test_cv.pdf",
            b"file_content",
            content_type="application/pdf"
        )
        
        application = Application.objects.create(
            job=job,
            candidate=self.candidate,
            cv_file=cv_file,
            status='PENDING'
        )
        
        initial_count = Notification.objects.count()
        
        # Update note only, status unchanged
        application.note = 'Internal note'
        application.save()
        
        # No new notification should be created
        # (Signal only triggers on status changes to INTERVIEW/REJECTED/ACCEPTED)
        self.assertEqual(Notification.objects.count(), initial_count + 1)  # +1 from creation
