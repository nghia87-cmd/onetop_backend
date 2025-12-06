# Generated migration for Soft Delete fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0001_initial'),  # Update với migration cuối cùng
    ]

    operations = [
        # Soft Delete fields đã có trong model (is_deleted, deleted_at)
        # từ SoftDeleteMixin, nên không cần thêm field
        
        # Chỉ cần tạo index cho is_deleted nếu chưa có
        migrations.AlterField(
            model_name='job',
            name='is_deleted',
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text='Whether this object has been soft-deleted'
            ),
        ),
        migrations.AlterField(
            model_name='job',
            name='deleted_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text='Timestamp when this object was soft-deleted'
            ),
        ),
    ]
