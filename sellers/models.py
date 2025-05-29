from django.db import models
from django.contrib.auth import get_user_model
from django_countries.fields import CountryField
from users.models import PaymentMethod
User = get_user_model()

def default_status():
        return {"onboard": False, "store_pm": False,"store_info": False}

class Seller(models.Model):
    user = models.OneToOneField(
        User, related_name="seller", on_delete=models.CASCADE)
    seller_id = models.CharField(max_length=100,unique=True)
    location = CountryField()
    status = models.JSONField(default=default_status)
    PG_verified = models.BooleanField(default=False)
    app_verified = models.BooleanField(default=False)
    pm_sub = models.OneToOneField(PaymentMethod,on_delete=models.CASCADE,null=True)
    

    
class Store(models.Model):
    seller = models.OneToOneField(Seller,related_name="store",on_delete=models.CASCADE)
    name = models.CharField(max_length=100,unique=True)
