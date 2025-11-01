from django.db import models
from django.contrib.auth import get_user_model
# Create your models here.
User = get_user_model()
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    items = models.JSONField(default=dict)  # List of item IDs or details