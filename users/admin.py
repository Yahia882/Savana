from django.contrib import admin
from .models import Address,PhoneNumber, AddressPhoneNumber
# Register your models here.
admin.site.register(Address)
admin.site.register(PhoneNumber)
admin.site.register(AddressPhoneNumber)