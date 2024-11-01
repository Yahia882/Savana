# Generated by Django 5.1.1 on 2024-10-30 20:43

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_alter_addressphonenumber_user'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='addressphonenumber',
            unique_together={('user', 'phone_number')},
        ),
    ]