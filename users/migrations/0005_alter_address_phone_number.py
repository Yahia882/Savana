# Generated by Django 5.1.1 on 2024-10-27 14:20

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_remove_phonenumber_is_primary_phonenumber_temp_phone_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='phone_number',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.addressphonenumber'),
        ),
    ]
