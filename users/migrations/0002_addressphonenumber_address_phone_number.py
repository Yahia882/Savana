# Generated by Django 5.1.1 on 2024-10-23 12:53

import django.db.models.deletion
import phonenumber_field.modelfields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AddressPhoneNumber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(max_length=128, region=None)),
                ('security_code', models.CharField(max_length=120, null=True)),
                ('is_verified', models.BooleanField(default=False)),
                ('sent', models.DateTimeField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name='address',
            name='phone_number',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='users.addressphonenumber'),
        ),
    ]
