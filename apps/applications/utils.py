# apps/applications/utils.py
from icalendar import Calendar, Event
from datetime import timedelta

def generate_ics_content(interview):
    """
    Tạo nội dung file .ics để đính kèm vào email
    """
    cal = Calendar()
    cal.add('prodid', '-//OneTop Recruitment//onetop.com//')
    cal.add('version', '2.0')

    event = Event()
    event.add('summary', f'Phỏng vấn: {interview.application.job.title}')
    event.add('dtstart', interview.interview_date)
    event.add('dtend', interview.interview_date + timedelta(minutes=interview.duration_minutes))
    event.add('dtstamp', interview.created_at)
    
    # Ưu tiên hiển thị Link Online, nếu không có thì hiện địa điểm
    location = interview.meeting_link if interview.meeting_link else interview.location
    event.add('location', location)
    
    description = f"Phỏng vấn vị trí: {interview.application.job.title}\n"
    description += f"Công ty: {interview.application.job.company.name}\n"
    if interview.note:
        description += f"Ghi chú: {interview.note}\n"
    if interview.meeting_link:
        description += f"Link tham gia: {interview.meeting_link}"
        
    event.add('description', description)

    # Thêm sự kiện vào lịch
    cal.add_component(event)
    
    return cal.to_ical()