"""
Custom throttling classes for OneTop Backend
"""
from rest_framework.throttling import UserRateThrottle
from django.conf import settings


class PDFGenerationThrottle(UserRateThrottle):
    """
    Giới hạn tần suất tạo PDF để tránh spam
    Default: 5 requests/hour per user (configurable via settings)
    """
    # CRITICAL FIX: Move to settings for production flexibility
    rate = getattr(settings, 'PDF_GENERATION_RATE', '5/hour')
    scope = 'pdf_generation'


class ApplicationSubmissionThrottle(UserRateThrottle):
    """
    Giới hạn số lượng đơn ứng tuyển
    Default: 20 applications/day per user (configurable via settings)
    """
    rate = getattr(settings, 'APPLICATION_SUBMISSION_RATE', '20/day')
    scope = 'application_submission'


class MessageSendThrottle(UserRateThrottle):
    """
    Giới hạn gửi tin nhắn để tránh spam
    Default: 100 messages/hour per user (configurable via settings)
    """
    rate = getattr(settings, 'MESSAGE_SEND_RATE', '100/hour')
    scope = 'message_send'
