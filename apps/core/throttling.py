"""
Custom throttling classes for OneTop Backend
"""
from rest_framework.throttling import UserRateThrottle


class PDFGenerationThrottle(UserRateThrottle):
    """
    Giới hạn tần suất tạo PDF để tránh spam
    5 requests/hour per user
    """
    rate = '5/hour'
    scope = 'pdf_generation'


class ApplicationSubmissionThrottle(UserRateThrottle):
    """
    Giới hạn số lượng đơn ứng tuyển
    20 applications/day per user
    """
    rate = '20/day'
    scope = 'application_submission'


class MessageSendThrottle(UserRateThrottle):
    """
    Giới hạn gửi tin nhắn để tránh spam
    100 messages/hour per user
    """
    rate = '100/hour'
    scope = 'message_send'
