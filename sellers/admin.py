from django.contrib import admin
from .models import ProductIdentity, Seller , PaymentMethod, Store , ProductVariation, Offer, SellerProduct
# Register your models here.
admin.site.register(Seller)
admin.site.register(PaymentMethod)
admin.site.register(Store)
admin.site.register(ProductIdentity)
admin.site.register(ProductVariation)
admin.site.register(Offer)
admin.site.register(SellerProduct)