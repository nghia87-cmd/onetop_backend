# Generated migration for Soft Delete + Unique Constraint fixes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('companies', '0001_initial'),  # Update với migration cuối cùng
    ]

    operations = [
        # 1. Add Soft Delete fields (from SoftDeleteMixin)
        migrations.AddField(
            model_name='company',
            name='is_deleted',
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text='Whether this object has been soft-deleted'
            ),
        ),
        migrations.AddField(
            model_name='company',
            name='deleted_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text='Timestamp when this object was soft-deleted'
            ),
        ),
        
        # 2. Remove old unique constraints
        migrations.AlterField(
            model_name='company',
            name='name',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='company',
            name='slug',
            field=models.SlugField(max_length=255, blank=True, db_index=True),
        ),
        
        # 3. Add new UniqueConstraint with condition (Partial Index)
        # Only enforce uniqueness on active (non-deleted) records
        migrations.AddConstraint(
            model_name='company',
            constraint=models.UniqueConstraint(
                fields=['name'],
                condition=models.Q(is_deleted=False),
                name='unique_active_company_name'
            ),
        ),
        migrations.AddConstraint(
            model_name='company',
            constraint=models.UniqueConstraint(
                fields=['slug'],
                condition=models.Q(is_deleted=False),
                name='unique_active_company_slug'
            ),
        ),
    ]
