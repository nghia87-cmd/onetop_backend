# Generated migration for database indexes optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),  # Update với migration cuối cùng của users app
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='job_posting_credits',
            field=models.IntegerField(db_index=True, default=0, help_text='Số lượt đăng tin còn lại'),
        ),
        migrations.AlterField(
            model_name='user',
            name='membership_expires_at',
            field=models.DateTimeField(blank=True, db_index=True, help_text='Ngày hết hạn gói dịch vụ', null=True),
        ),
    ]
