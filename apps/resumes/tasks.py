import logging
from celery import shared_task
# [FIX] Import đúng thư viện chứa render_to_string
from django.template.loader import render_to_string 
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.utils import timezone # Cần thêm import này nếu chưa có
from django.utils.translation import gettext as _  # Use gettext (not lazy) for runtime

from weasyprint import HTML 
from apps.resumes.models import Resume

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_resume_pdf_async(self, resume_id):
    """
    Task bất đồng bộ để tạo file PDF CV bằng WeasyPrint (tốn CPU).
    """
    try:
        resume = Resume.objects.get(id=resume_id)
        
        # 1. Render HTML
        context = {'resume': resume, 'user': resume.user}
        html_content = render_to_string('resumes/harvard_pdf.html', context)
        
        # 2. Render PDF bằng WeasyPrint
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        # 3. Lưu file PDF vào trường FileField
        filename = f"resume_{resume.user.id}_{resume_id}_{timezone.now().strftime('%Y%m%d')}.pdf"
        
        content_file = ContentFile(pdf_bytes, name=filename)
        
        # Cập nhật và lưu
        resume.pdf_file.save(filename, content_file, save=True)

        logger.info(f"Successfully generated and saved PDF for Resume ID: {resume_id}")

        # 4. Gửi thông báo/Email cho người dùng
        download_url = resume.pdf_file.url
        
        # Kiểm tra xem có email user không trước khi gửi
        if resume.user.email:
            try:
                send_mail(
                    subject=str(_('Your CV is ready for download')),
                    message=_("Your CV ({title}) has been successfully created. Download at: {url}").format(
                        title=resume.title,
                        url=download_url
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[resume.user.email],
                    fail_silently=True, # Không raise lỗi nếu gửi mail thất bại
                )
            except Exception as e:
                logger.error(f"Failed to send email for resume {resume_id}: {e}")

        return f"PDF generated and saved for Resume ID: {resume_id}"

    except Resume.DoesNotExist:
        logger.error(f"Resume with ID {resume_id} does not exist.")
        # Không retry nếu object không tồn tại
        return f"Resume {resume_id} not found."
    except Exception as exc:
        logger.error(f"PDF generation failed for Resume ID {resume_id}: {exc}")
        raise self.retry(exc=exc)