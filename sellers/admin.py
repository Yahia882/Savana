from django.contrib import admin
from .models import Seller , PaymentMethod, Store
# Register your models here.
admin.site.register(Seller)
admin.site.register(PaymentMethod)
admin.site.register(Store)
