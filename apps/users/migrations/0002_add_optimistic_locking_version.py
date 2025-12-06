# Generated migration for adding Optimistic Locking version field to User model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='version',
            field=models.IntegerField(
                default=0,
                help_text='Version field for optimistic locking - auto-incremented on each update'
            ),
        ),
    ]
