# apps/applications/tasks.py
import logging
from celery import shared_task
from django.core.mail import EmailMessage
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from .models import InterviewSchedule
from .utils import generate_ics_content

logger = logging.getLogger(__name__)

@shared_task
def send_interview_invitation_email(interview_id):
    """
    Gửi email mời phỏng vấn kèm file .ics
    """
    try:
        interview = InterviewSchedule.objects.select_related(
            'application__candidate', 'application__job__company'
        ).get(id=interview_id)
        
        candidate = interview.application.candidate
        job = interview.application.job
        
        subject = f"📅 Thư mời phỏng vấn: {job.title} tại {job.company.name}"
        body = f"""
        Xin chào {candidate.full_name},
        
        Công ty {job.company.name} trân trọng mời bạn tham gia buổi phỏng vấn cho vị trí {job.title}.
        
        ⏰ Thời gian: {interview.interview_date.strftime('%H:%M %d/%m/%Y')}
        📍 Địa điểm/Link: {interview.meeting_link or interview.location}
        📝 Ghi chú: {interview.note}
        
        Vui lòng kiểm tra file lịch (.ics) đính kèm để thêm vào lịch của bạn.
        
        Trân trọng,
        OneTop Recruitment Team
        """
        
        email = EmailMessage(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [candidate.email],
        )
        
        # Đính kèm file .ics
        ics_content = generate_ics_content(interview)
        email.attach('interview_invite.ics', ics_content, 'text/calendar')
        
        email.send(fail_silently=False)
        logger.info(f"Sent interview invite to {candidate.email}")
        
    except Exception as e:
        logger.error(f"Error sending interview invite: {e}")

@shared_task
def check_upcoming_interviews():
    """
    Task chạy định kỳ: Gửi nhắc nhở trước 1 tiếng
    """
    now = timezone.now()
    one_hour_later = now + timedelta(hours=1)
    # Tìm các buổi phỏng vấn sắp diễn ra trong khoảng 1h -> 1h5p tới (tránh gửi lặp)
    upcoming_interviews = InterviewSchedule.objects.filter(
        status='SCHEDULED',
        interview_date__gte=one_hour_later,
        interview_date__lte=one_hour_later + timedelta(minutes=5)
    ).select_related('application__candidate', 'application__job')
    
    count = 0
    for interview in upcoming_interviews:
        candidate = interview.application.candidate
        subject = f"🔔 Nhắc nhở: Bạn có lịch phỏng vấn sau 1 tiếng nữa!"
        body = f"Đừng quên buổi phỏng vấn vị trí {interview.application.job.title} lúc {interview.interview_date.strftime('%H:%M')} nhé!"
        
        try:
            email = EmailMessage(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [candidate.email]
            )
            email.send()
            count += 1
        except Exception as e:
            logger.error(f"Failed to remind {candidate.email}: {e}")
            
    return f"Sent reminders for {count} interviews."