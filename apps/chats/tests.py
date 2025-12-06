from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .models import Conversation, Message
from apps.jobs.models import Job
from apps.companies.models import Company

User = get_user_model()


class ConversationModelTest(TestCase):
    """Test cho Conversation Model"""

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
        
        self.conversation = Conversation.objects.create(
            participant1=self.candidate,
            participant2=self.recruiter,
            job=self.job
        )

    def test_conversation_creation(self):
        """Test tạo conversation thành công"""
        self.assertEqual(self.conversation.participant1, self.candidate)
        self.assertEqual(self.conversation.participant2, self.recruiter)
        self.assertEqual(self.conversation.job, self.job)

    def test_conversation_str_representation(self):
        """Test __str__ method"""
        expected = f"Chat: {self.candidate.email} & {self.recruiter.email}"
        self.assertEqual(str(self.conversation), expected)

    def test_conversation_unique_constraint(self):
        """Test không thể tạo conversation trùng lặp"""
        with self.assertRaises(Exception):
            Conversation.objects.create(
                participant1=self.candidate,
                participant2=self.recruiter,
                job=self.job
            )

    def test_conversation_ordering(self):
        """Test conversation được sắp xếp theo last_message_at"""
        # Tạo conversation mới
        new_conversation = Conversation.objects.create(
            participant1=self.candidate,
            participant2=self.recruiter
        )
        
        # Update last_message_at của conversation cũ
        self.conversation.last_message_at = timezone.now() + timedelta(seconds=1)
        self.conversation.save()
        
        conversations = Conversation.objects.all()
        self.assertEqual(conversations[0], self.conversation)

    def test_conversation_without_job(self):
        """Test conversation có thể không liên kết với job"""
        conversation = Conversation.objects.create(
            participant1=self.candidate,
            participant2=self.recruiter
        )
        self.assertIsNone(conversation.job)


class MessageModelTest(TestCase):
    """Test cho Message Model"""

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
        
        self.conversation = Conversation.objects.create(
            participant1=self.candidate,
            participant2=self.recruiter
        )
        
        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.candidate,
            text='Hello recruiter!'
        )

    def test_message_creation(self):
        """Test tạo message thành công"""
        self.assertEqual(self.message.conversation, self.conversation)
        self.assertEqual(self.message.sender, self.candidate)
        self.assertEqual(self.message.text, 'Hello recruiter!')

    def test_message_str_representation(self):
        """Test __str__ method"""
        expected = f"Msg from {self.candidate.email}"
        self.assertEqual(str(self.message), expected)

    def test_message_default_is_read(self):
        """Test is_read mặc định là False"""
        self.assertFalse(self.message.is_read)

    def test_message_ordering(self):
        """Test messages được sắp xếp theo created_at"""
        message2 = Message.objects.create(
            conversation=self.conversation,
            sender=self.recruiter,
            text='Hello candidate!'
        )
        
        messages = Message.objects.filter(conversation=self.conversation)
        self.assertEqual(messages[0], self.message)
        self.assertEqual(messages[1], message2)

    def test_message_with_attachment(self):
        """Test message có attachment"""
        file = SimpleUploadedFile(
            "test_file.txt",
            b"file content",
            content_type="text/plain"
        )
        
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.candidate,
            text='File attached',
            attachment=file
        )
        
        self.assertIsNotNone(message.attachment)


class ConversationAPITest(APITestCase):
    """Test cho Conversation API"""

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
        
        self.other_user = User.objects.create_user(
            email='other@test.com',
            username='other@test.com',
            password='testpass123',
            full_name='Other User',
            user_type='CANDIDATE'
        )
        
        self.conversation = Conversation.objects.create(
            participant1=self.candidate,
            participant2=self.recruiter
        )
        
        self.conversations_url = reverse('v1:conversation-list')

    def test_list_user_conversations(self):
        """Test user chỉ xem được conversations của mình"""
        self.client.force_authenticate(user=self.candidate)
        
        response = self.client.get(self.conversations_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_other_user_cannot_see_conversation(self):
        """Test user khác không thấy conversation không liên quan"""
        self.client.force_authenticate(user=self.other_user)
        
        response = self.client.get(self.conversations_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_get_conversation_messages(self):
        """Test lấy messages trong conversation"""
        Message.objects.create(
            conversation=self.conversation,
            sender=self.candidate,
            text='Message 1'
        )
        
        Message.objects.create(
            conversation=self.conversation,
            sender=self.recruiter,
            text='Message 2'
        )
        
        self.client.force_authenticate(user=self.candidate)
        
        url = reverse('v1:conversation-messages', args=[self.conversation.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_unauthorized_cannot_access_messages(self):
        """Test user không liên quan không thể xem messages"""
        self.client.force_authenticate(user=self.other_user)
        
        url = reverse('v1:conversation-messages', args=[self.conversation.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_conversation(self):
        """Test tạo conversation mới"""
        self.client.force_authenticate(user=self.candidate)
        
        new_user = User.objects.create_user(
            email='newuser@test.com',
            username='newuser@test.com',
            password='testpass123',
            full_name='New User',
            user_type='RECRUITER'
        )
        
        data = {
            'participant1': self.candidate.id,
            'participant2': new_user.id
        }
        
        response = self.client.post(self.conversations_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Conversation.objects.filter(
                participant1=self.candidate,
                participant2=new_user
            ).exists()
        )

    def test_unauthenticated_cannot_access(self):
        """Test chưa đăng nhập không thể truy cập"""
        response = self.client.get(self.conversations_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MessageAPITest(APITestCase):
    """Test cho Message operations"""

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
        
        self.conversation = Conversation.objects.create(
            participant1=self.candidate,
            participant2=self.recruiter
        )

    def test_send_message(self):
        """Test gửi message"""
        self.client.force_authenticate(user=self.candidate)
        
        messages_url = reverse('v1:message-list')
        data = {
            'conversation': self.conversation.id,
            'text': 'Hello from candidate'
        }
        
        response = self.client.post(messages_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Message.objects.filter(
                conversation=self.conversation,
                sender=self.candidate,
                text='Hello from candidate'
            ).exists()
        )

    def test_mark_message_as_read(self):
        """Test đánh dấu message đã đọc"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.candidate,
            text='Test message',
            is_read=False
        )
        
        self.client.force_authenticate(user=self.recruiter)
        
        url = reverse('v1:message-detail', args=[message.id])
        data = {'is_read': True}
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        message.refresh_from_db()
        self.assertTrue(message.is_read)

    def test_send_message_with_attachment(self):
        """Test gửi message kèm file"""
        self.client.force_authenticate(user=self.candidate)
        
        file = SimpleUploadedFile(
            "document.pdf",
            b"PDF content",
            content_type="application/pdf"
        )
        
        messages_url = reverse('v1:message-list')
        data = {
            'conversation': self.conversation.id,
            'text': 'Document attached',
            'attachment': file
        }
        
        response = self.client.post(messages_url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        message = Message.objects.get(text='Document attached')
        self.assertIsNotNone(message.attachment)

    def test_message_ordering_in_conversation(self):
        """Test messages được sắp xếp đúng thứ tự"""
        Message.objects.create(
            conversation=self.conversation,
            sender=self.candidate,
            text='Message 1'
        )
        
        Message.objects.create(
            conversation=self.conversation,
            sender=self.recruiter,
            text='Message 2'
        )
        
        Message.objects.create(
            conversation=self.conversation,
            sender=self.candidate,
            text='Message 3'
        )
        
        self.client.force_authenticate(user=self.candidate)
        
        url = reverse('v1:conversation-messages', args=[self.conversation.id])
        response = self.client.get(url)
        
        messages = response.data['results']
        self.assertEqual(messages[0]['text'], 'Message 1')
        self.assertEqual(messages[1]['text'], 'Message 2')
        self.assertEqual(messages[2]['text'], 'Message 3')
