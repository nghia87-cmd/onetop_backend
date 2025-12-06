from django.core.exceptions import ValidationError

def validate_file_size(value):
    limit = 5 * 1024 * 1024  # 5 MB
    if value.size > limit:
        raise ValidationError(f'Dung lượng file quá lớn. Vui lòng tải lên file nhỏ hơn {limit / (1024 * 1024)}MB.')