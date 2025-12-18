from django.db import models
from django.contrib.auth import get_user_model
from django_countries.fields import CountryField
from users.models import PaymentMethod
User = get_user_model()

BRAND_CHOICES = (
    ("generic", "Generic"),
    ("eva", "EVA Pharma"),
    ("global_napi", "Global Napi Pharma"),
    ("apex", "APEX Pharma S.A.E."),
)
PRODUCT_TYPE_CHOICES = (
    # at the mean time only implemet med, clothes and shoes
    ("over_the_counter_drugs", "Drugs -> Over The Counter Drugs"),
    ("prescription_drugs", "Drugs -> Prescription Drugs"),
    ("medical_supplies", "Medicines -> Medical Supplies"),
    ("clothes", "Clothes"),
    ("tshirt", "Clothes -> T-Shirt"),
    ("shoes", "Shoes"),
    ("electronics", "Electronics"),
    ("furniture", "Furniture"),
    ("books", "Books"),
    ("toys", "Toys"),
    ("accessories", "Accessories"),
    ("sports_clothes", "Sports -> Clothes"),
    ("sports_shoes", "Sports -> Shoes"),
    ("jewelry", "Jewelry"),
    ("beauty", "Beauty"),
    ("automotive", "Automotive"),
    ("pet_supplies", "Pet Supplies"),
    ("home_appliances", "Home Appliances"),
    ("generic", "Generic"),
    ("smartphone", "Electronics -> Smartphone"),
    ("laptop", "Electronics -> Laptop"),
)
DOSAGE_FORM_CHOICES = (
    ('tablet', 'Tablet'),
    ('capsule', 'Capsule'),
    ('syrup', 'Syrup'),
    ('suspension', 'Suspension'),
    ('injection', 'Injection'),
    ('cream', 'Cream'),
    ('ointment', 'Ointment'),
    ('gel', 'Gel'),
    ('powder', 'Powder'),
    ('solution', 'Solution'),
    ('drops', 'Drops'),
    ('inhaler', 'Inhaler'),
    ('patch', 'Transdermal Patch'),  # Clarified Patch
    ('suppository', 'Suppository'),
    ('lozenge', 'Lozenge'),
    ('spray', 'Spray'),
    ('gas', 'Gas'),
    ('liquid', 'Liquid'),
    ('granule', 'Granules'),
    ('elixir', 'Elixir'),
    ('emulsion', 'Emulsion'),
    ('foam', 'Foam'),
    ('jelly', 'Jelly'),
    ('implant', 'Implant'),
    ('kit', 'Kit'),
    ('aerosol', 'Aerosol'),
    ('paste', 'Paste'),
    ('other', 'Other'),
)
AGE_CHOICES = (
    ('newborn', 'Newborn (0–1 month)'),
    ('infant', 'Infant (1 month – 1 year)'),
    ('toddler', 'Toddler (1–3 years)'),
    ('child', 'Child (4–12 years)'),
    ('teenager', 'Teenager (13–19 years)'),
    ('adult', 'Adult (20–64 years)'),
    ('senior', 'Senior (65+ years)'),
    ('all_ages', 'All Ages'),
)
PRODUCT_CONDITION_CHOICES = (
    ('new', 'New'),
    ('used', 'Used'),
    ('refurbished', 'Refurbished'),
)

def default_status():
    return {"onboard": False, "store_pm": False, "store_info": False}

STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
# for performance purposes (related to search) you migh make composite index on status and item_name maybe product_type also idk
# for the mean time i will just index status to show products efficiently to the customers 
class ProductIdentity(models.Model):
    item_name = models.CharField(max_length=300)
    product_type = models.CharField(
        max_length=50, choices=PRODUCT_TYPE_CHOICES)
    has_variations = models.BooleanField(default=False)
    brand_name = models.CharField(max_length=50, choices=BRAND_CHOICES)

    product_description = models.TextField(blank=True, null=True)
    bullet_points = models.JSONField(default=list, blank=True, null=True)
    product_details = models.JSONField(default=dict,)
    product_variations = models.JSONField(default=dict, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        db_index=True   # important for performance
    )
    tax_code = models.CharField(max_length=20, default="txcd_32020002")
    sripe_product_id = models.CharField(max_length=100, blank=True, null=True)
    class Meta:
        permissions = [
            ("can_change_status", "Can Change Status"),
        ]

class Seller(models.Model):
    user = models.OneToOneField(
        User, related_name="seller", on_delete=models.CASCADE)
    seller_id = models.CharField(max_length=100, unique=True)
    location = CountryField()
    status = models.JSONField(default=default_status)
    PG_verified = models.BooleanField(default=False)
    app_verified = models.BooleanField(default=False)
    # change null to false the seller must have a payment method
    pm_sub = models.OneToOneField(
        PaymentMethod, on_delete=models.CASCADE, null=True)
    product = models.ManyToManyField(
        ProductIdentity, related_name="seller", blank=True, through='SellerProduct')
    draft_data = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        permissions = [
            ("can_verify_seller", "Can verify seller"),
        ]


class Store(models.Model):
    seller = models.OneToOneField(
        Seller, related_name="store", on_delete=models.CASCADE)
    name = models.CharField(max_length=100, unique=True)


class ProductVariation(models.Model):
    product_identity = models.ForeignKey(
        ProductIdentity, related_name="variations", on_delete=models.CASCADE)
    upc = models.CharField(max_length=14, unique=True)
    # color red size M material cotton
    theme = models.JSONField(default=dict, blank=True, null=True)
    # images = models.FileField(upload_to='product_images/', blank=True, null=True)
    default = models.BooleanField(default=False)


class Offer(models.Model):
    sku = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    PV = models.ForeignKey(
        ProductVariation, related_name="offers", on_delete=models.CASCADE)
    seller = models.ForeignKey(
        Seller, related_name="offers", on_delete=models.CASCADE)
    condition = models.CharField(
         max_length=50, choices=PRODUCT_CONDITION_CHOICES, default='new')
    fullfillment_channel = models.CharField(
        max_length=50, choices=[('FBM', 'Fulfilled by Merchant'), ('FBA', 'Fulfilled by Amazon')], default='FBM')
    discounted_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    class Meta:
        unique_together = ('PV', 'seller')


class SellerProduct(models.Model):
    seller = models.ForeignKey(
        Seller, related_name="products", on_delete=models.CASCADE)
    product_identity = models.ForeignKey(
        ProductIdentity, related_name="sellers", on_delete=models.CASCADE)
    variations  = models.JSONField(default=dict, blank=True, null=True)
    default = models.BooleanField(default=False)
    class Meta:
        unique_together = ('seller', 'product_identity')

