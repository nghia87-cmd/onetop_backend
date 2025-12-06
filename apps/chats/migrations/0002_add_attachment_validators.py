# Generated migration for adding file validators to Chat attachment

from django.db import migrations, models
import django.core.validators
import apps.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('chats', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='attachment',
            field=models.FileField(
                blank=True,
                help_text='Allowed: PDF, DOC, DOCX, JPG, PNG, GIF, ZIP. Max size: 5MB',
                null=True,
                upload_to='chat_attachments/',
                validators=[
                    apps.core.validators.validate_file_size,
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'zip']
                    )
                ]
            ),
        ),
    ]
