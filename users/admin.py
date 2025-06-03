from django.contrib import admin
from .models import Address,PhoneNumber, AddressPhoneNumber, Customer
# Register your models here.
admin.site.register(Address)
admin.site.register(PhoneNumber)
admin.site.register(AddressPhoneNumber)
admin.site.register(Customer)