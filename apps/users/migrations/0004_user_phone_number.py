# Generated manually for adding phone_number field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_merge_20251207_0541'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='phone_number',
            field=models.CharField(blank=True, default='', help_text='Số điện thoại liên hệ', max_length=15, verbose_name='Phone Number'),
        ),
    ]
