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
        
        # CRITICAL FIX: Exclude soft-deleted jobs to prevent ghost records in search results
        queryset_pagination = 10000
        
        def get_queryset(self):
            """Override to exclude soft-deleted jobs from Elasticsearch index"""
            return super().get_queryset().filter(is_deleted=False)
        
        # Tự động cập nhật ES khi model thay đổi
        # ignore_signals = True # Bật lên nếu muốn update thủ công bằng Cronjob để tối ưu write DB