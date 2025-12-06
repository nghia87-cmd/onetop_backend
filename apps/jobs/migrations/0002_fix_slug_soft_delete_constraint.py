# Generated migration for fixing Job slug unique constraint with soft delete

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0001_initial'),
    ]

    operations = [
        # Step 1: Remove unique=True from slug field
        migrations.AlterField(
            model_name='job',
            name='slug',
            field=models.SlugField(blank=True, db_index=True, max_length=255),
        ),
        
        # Step 2: Add partial unique constraint (only for active jobs)
        migrations.AddConstraint(
            model_name='job',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_deleted', False)),
                fields=('slug',),
                name='unique_active_job_slug'
            ),
        ),
        
        # Step 3: Add Meta class with ordering and constraints
        migrations.AlterModelOptions(
            name='job',
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Công việc',
                'verbose_name_plural': 'Công việc'
            },
        ),
    ]
