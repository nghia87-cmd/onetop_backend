# apps/jobs/documents.py

from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry
from .models import Job

@registry.register_document
class JobDocument(Document):
    # Index thông tin Company để tìm kiếm (Nested Field)
    company = fields.ObjectField(properties={
        'name': fields.TextField(),
        'id': fields.IntegerField(),
        'slug': fields.KeywordField(),
    })

    # Các trường Text hỗ trợ tìm kiếm mờ (fuzzy), đồng nghĩa...
    title = fields.TextField(
        attr='title',
        fields={
            'raw': fields.KeywordField(), # Để sort hoặc filter chính xác
            'suggest': fields.CompletionField(), # Để làm tính năng Auto-complete
        }
    )
    description = fields.TextField()
    requirements = fields.TextField()
    location = fields.TextField()
    
    # Các trường Filter
    job_type = fields.KeywordField()
    status = fields.KeywordField()
    salary_max = fields.IntegerField()
    created_at = fields.DateField()
    views_count = fields.IntegerField()
    
    # CRITICAL FIX: Index is_deleted field to prevent ghost records
    # Lọc ở search thay vì queryset để ES có thể xóa record khi soft delete
    is_deleted = fields.BooleanField()

    class Index:
        # Tên index trong Elasticsearch
        name = 'jobs'
        # Cấu hình replicas/shards (tùy chọn)
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = Job # Model được map
        
        # Các trường lấy trực tiếp từ model
        fields = [
            'id',
            'slug',
        ]
        
        queryset_pagination = 10000
        
        # CRITICAL FIX #1: Phải dùng all_objects để ES có thể update/delete soft-deleted jobs
        # Nếu dùng default manager (SoftDeleteManager), khi job.delete() được gọi:
        # - Signal post_save kích hoạt
        # - ES thư viện gọi Job.objects.get(id=...) để lấy dữ liệu mới
        # - SoftDeleteManager chặn job đã xóa -> DoesNotExist
        # - ES bỏ qua việc update -> Ghost record
        def get_queryset(self):
            """Force use all_objects manager to include soft-deleted jobs"""
            return self.model.all_objects.all()
        
        # Tự động cập nhật ES khi model thay đổi
        # ignore_signals = True # Bật lên nếu muốn update thủ công bằng Cronjob để tối ưu write DB