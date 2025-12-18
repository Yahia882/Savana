from datetime import timedelta
from time import timezone
from django.db import models
from django.contrib.auth import get_user_model
from sellers.models import ProductIdentity, ProductVariation, Store, Offer
from users.models import Address, PaymentMethod
User = get_user_model()


class Cart(models.Model):
    user = models.OneToOneField(User,related_name="cart", on_delete=models.CASCADE)
    items = models.JSONField(default=dict)  # List of item IDs or details



class Checkout(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_total = models.DecimalField(max_digits=10, decimal_places=2,default=0) # total_price + shipping_cost + tax - discount
    shipping_address = models.ForeignKey(Address, on_delete=models.SET_NULL, related_name='used_checkout')#this shit is wrong
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.ForeignKey(PaymentMethod,on_delete=models.SET_NULL,related_name="used_checkout",null=True,blank=True)
    payment_session_id = models.CharField(max_length=255,)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at=models.DateTimeField()
    soft_expires_at = models.DateTimeField()


class CheckoutItem(models.Model):
    checkout = models.ForeignKey(Checkout, related_name='items', on_delete=models.CASCADE)
    product_identity = models.ForeignKey(ProductIdentity, on_delete=models.PROTECT)
    product_variation = models.ForeignKey(ProductVariation, on_delete=models.PROTECT)
    offer = models.OneToOneField(Offer,on_delete=models.PROTECT) # what if the seller deletes the offer or somehow the stock is over
    store = models.ForeignKey(Store,on_delete=models.PROTECT)    # we have to prevent this senario
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Available'),
            ('unavailable', 'Unavailable'),
            ('price_changed', 'Price Changed'),
        ],
        default='available'
    )