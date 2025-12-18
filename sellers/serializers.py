from datetime import datetime
from rest_framework import serializers
from django_countries.serializer_fields import CountryField
from .models import ProductVariation, Store, Seller, BRAND_CHOICES, PRODUCT_TYPE_CHOICES, AGE_CHOICES, DOSAGE_FORM_CHOICES, PRODUCT_CONDITION_CHOICES
from users.models import PaymentMethod
from django_countries.serializers import CountryFieldMixin
from dj_rest_auth.app_settings import api_settings
import biip
import itertools
import re


def generate_variations(attributes):

    # Get the names of the attributes
    attribute_names = list(attributes.keys())
    attribute_options = list(attributes.values())

    # Use itertools.product to get all possible combinations
    combinations = itertools.product(*attribute_options)

    variations = {}
    id_counter = 1

    # Iterate through each combination to create a variation object
    for combo in combinations:
        # Create the theme dictionary
        theme = {}
        for name, value in zip(attribute_names, combo):
            theme[name] = value

        variations[id_counter] = {"theme": theme}
        id_counter += 1

    return variations


class CustomizedJWTSerializer(serializers.Serializer):
    """
    Serializer for JWT authentication.
    """
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = serializers.SerializerMethodField()
    status = serializers.CharField()

    def get_user(self, obj):
        """
        Required to allow using custom USER_DETAILS_SERIALIZER in
        JWTSerializer. Defining it here to avoid circular imports
        """
        JWTUserDetailsSerializer = api_settings.USER_DETAILS_SERIALIZER

        user_data = JWTUserDetailsSerializer(
            obj['user'], context=self.context).data
        return user_data


class LocationSerializer(serializers.Serializer):
    country = CountryField()

    ALLOWED_COUNTRIES = {
        "AU", "AT", "BE", "BR", "BG", "CA", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GI", "GR", "HK", "HU", "IE", "IT", "JP", "LV", "LI", "LT", "LU", "MY",
        "MT", "MX", "NL", "NZ", "NO", "PL", "PT", "RO", "SG", "SK", "SI", "ES", "SE",
        "CH", "TH", "AE", "GB", "US"
    }

    def validate_country(self, value):
        self.allowed = False
        if value in self.ALLOWED_COUNTRIES:
            self.allowed = True
        self.context["allowed"] = self.allowed
        return value


class StoreInfoSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=100)
    seller = serializers.CharField(source="seller.id", read_only=True)

    class Meta:
        model = Store
        fields = ["seller", 'name']

    def validate_name(self, value):
        if Store.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                "A store with this name already exists.")
        return value

    def create(self, validated_data):
        seller = self.context['request'].user.seller
        instance = Store.objects.create(
            name=validated_data['name'], seller=seller)
        return instance


class VerifySellerSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    PG_verified = serializers.BooleanField(read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    location = serializers.CharField(read_only=True)

    class Meta:
        model = Seller
        fields = ['id', 'location', 'PG_verified',
                  'app_verified', "store_name"]


class PaymentMethodSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentMethod
        fields = "__all__"


class GetSellerSerializer(CountryFieldMixin, serializers.ModelSerializer):
    store_name = serializers.CharField(source='store.name')
    payment_method = PaymentMethodSerializer(source='pm_sub',)

    class Meta:
        model = Seller
        fields = [
            "id", "user", "seller_id", "location", "status", "PG_verified", "app_verified", "pm_sub",
            "store_name", "payment_method"
        ]

# product identity step 1 of creating a product

def get_tax_code(product_type):
    tax_code_mapping = {
        "over_the_counter_drugs": "txcd_32020002",
        "prescription_drugs": "txcd_32020001",
        "medical_supplies": "txcd_32070028",
        "clothes": "txcd_30011000",
        "tshirt": "txcd_30011000",
        "shoes": "txcd_30011000",
    }
    return tax_code_mapping.get(product_type, "txcd_32020002")

class ProductIdentitySerializer(serializers.Serializer):
    item_name = serializers.CharField(max_length=100)
    product_type = serializers.ChoiceField(choices=PRODUCT_TYPE_CHOICES)
    has_variations = serializers.BooleanField(
        default=False, required=False)
    # what happens to the products with matching UPCs?
    brand_name = serializers.ChoiceField(choices=BRAND_CHOICES)

    def save(self):
        seller = self.context['request'].user.seller
        seller.draft_data['tmp'] = {"ProductIdentity": self.validated_data}
        seller.draft_data['tmp']["ProductIdentity"].update({"tax_code": get_tax_code(self.validated_data['product_type'])})
        seller.save()

# product variation also part of step 1 u select one serilizer based on product type that logic is implemented in the view


VALID_MASS_UNITS = ["mg", "g","mcg",]
VALID_LIQUID_UNITS = ["ml", "l", "liter", "fl oz",]
LIQUID_FORMS = ['syrup', 'suspension', 'solution',
                'elixir', 'emulsion', 'drops', 'liquid', "injection",]
SOLID_FORMS = ["ointment", "gel", "powder", "foam", "paste", "cream",]
SPECIAL_SOLID = ['tablet', 'capsule', 'granule', 'lozenge', 'suppository']
plural_special_solid = {"tablet": "tablets", "capsule": "capsules",
                        "granule": "granules", "lozenge": "lozenges", "suppository": "suppositories"}


class MedicalVariationSerializer(serializers.Serializer):
    dosage_form = serializers.ChoiceField(
        choices=DOSAGE_FORM_CHOICES)  # e.g. tablet
    pack_size = serializers.ListField(
        # array of possible sizes
        required=False, min_length=2, child=serializers.IntegerField(min_value=1),)
    size = serializers.ListField(
        required=False, min_length=2,)  # array of possible sizes
    strength = serializers.ListField(
        required=False, min_length=2,)  # e.g. 500mg
    age = serializers.ListField(
        required=False, min_length=2)  # e.g. "adult", "child"
    # maybe allow to buy individual tablets.

    def validate_strength(self, value):
        Unit = value[0].strip().split()[1]
        for val in value:
            pattern = r'^\d+(\.\d+)?\s*(mg|g|kg|mcg|ng|L|mL|cc|U|mEq|%)?$'
            if not re.match(pattern, val):
                raise serializers.ValidationError(
                    "Invalid strength format. Examples: '100 mg', '2 g', '500 U', '3 %'."
                )
            amount, unit = val.split()
            try:
                num = float(amount)
                if num <= 0:
                    raise ValueError
            except (ValueError, IndexError):
                raise serializers.ValidationError(
                    "Strength value must be a positive number."
                )
            if Unit != unit:
                raise serializers.ValidationError(
                    "All strength entries must use the same unit."
                )
        return value

    def validate_age(self, value):
        for val in value:
            if val not in AGE_CHOICES:
                try:
                    x, y = map(int, val.split('-'))
                except (ValueError, AttributeError):
                    raise serializers.ValidationError(
                        "Age range must be in format 'X-Y' (e.g., '10-20').")

            if x >= y:
                raise serializers.ValidationError(
                    "First age (X) must be less than second age (Y).")

            if x < 0 or y > 120:
                raise serializers.ValidationError(
                    "Ages must be between 0 and 120.")
        return value

    def validate_pack_size(self, value):
        dosage_form = self.initial_data.get("dosage_form")
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Pack sizes must be unique.")
        count = -1
        for val in value:
            count += 1
            if dosage_form in SPECIAL_SOLID:
                if val == 1:
                    val = f'{str(val)} {dosage_form}'
                else:
                    val = f'{str(val)} {plural_special_solid[dosage_form]}'
                value[count] = val
            else:
                if val == 1:
                    val = f'{str(val)} item'
                else:
                    val = f'{str(val)} items'
                value[count] = val
        return value

    def validate_size(self, value):
        Unit = value[0].strip().split()[1]
        index = -1
        for val in value:
            index += 1
            pattern = r'^\d+(\.\d+)?\s(mg|g|kg|mcg|ng|ml|l|liter|fl oz|cc|mL|L|U|mEq|%)$'
            if not re.match(pattern, val):
                raise serializers.ValidationError(
                    "Invalid size format. Examples: '100 mg', '2 g', '500 U', '3 %'."
                )
            num_part, unit = value.split()
            try:
                num = float(num_part)
                if num <= 0:
                    raise serializers.ValidationError(
                        "Size value must be a positive number.")
            except ValueError:
                raise serializers.ValidationError(
                    "Size value must be a valid number.")
            if Unit != unit:
                raise serializers.ValidationError(
                    "All strength entries must use the same unit."
                )
            
        return value

    def validate(self, data):
        dosage_form = data.get("dosage_form",None)
        if dosage_form is None:
            dosage_form = self.context['request'].user.seller.draft_data['tmp']["ProductIdentity"]["product_details"]["dosage_form"]
        Data = [v for v in [data.get("size"), data.get("strength")] if v is not None]
        for value in Data:
            for v in value:
                unit = v.strip().split()[1]
                if dosage_form in LIQUID_FORMS:
                    if unit not in VALID_LIQUID_UNITS:
                        raise serializers.ValidationError(
                            f"Invalid unit '{unit}' for liquid dosage form. Valid liquid units: {VALID_LIQUID_UNITS}"
                        )
                elif dosage_form in SOLID_FORMS:
                    if unit not in VALID_MASS_UNITS:
                        raise serializers.ValidationError(
                            f"Invalid unit '{unit}' for solid dosage form. Valid mass units: {VALID_MASS_UNITS}"
                        )
            
        return data

    def save(self):
        # this portion of code is used in other variation serializers as well
        seller = self.context['request'].user.seller
        var = self.validated_data
        seller.draft_data['tmp']["ProductIdentity"].update({
            "product_details": {"dosage_form": var.pop("dosage_form")}})
        seller.draft_data['tmp']["ProductIdentity"].update({
            "product_variations": var})
        seller.draft_data['tmp'].update({
            "possible_variation": generate_variations(var)})
        seller.save()
        return seller.draft_data['tmp']["possible_variation"]


# to be continued
class ClothesVariationSerializer(serializers.Serializer):
    size = serializers.ListField(
        required=False, min_length=2)  # array of possible sizes
    color = serializers.ListField(
        required=False, min_length=2)  # array of possible colors
    # validate size array
    # validate color array

# to be continued


class VariationParametersG2Serializer(serializers.Serializer):
    size = serializers.ListField(
        min_length=2, required=False)  # array of possible sizes
    flavor = serializers.ListField(
        min_length=2, required=False)  # array of possible colors
    # validate size array
    # validate flavor array

# based on variation theme make the field reuired or not based on product variations parameters


class OfferSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=100)  # offer
    UPC = serializers.CharField( )
    price = serializers.CharField(max_length =10)  # offer
    stock = serializers.IntegerField(default=0)  # offer
    image = serializers.ImageField(  # variation
        max_length=100, required = False)
    condition = serializers.ChoiceField(  # offer
        choices=PRODUCT_CONDITION_CHOICES, default="new")
    fullfilled_by = serializers.CharField(  # offer
        max_length=100, default="seller")
    default = serializers.BooleanField(default=False)

    def validate_UPC(self, value):
        try:
            value = biip.parse(value).gtin.value.zfill(14)
        except:
            raise serializers.ValidationError("{} is invalid UPC/GTIN code.".format(value))
        if ProductVariation.objects.filter(upc=value).exists():
            raise serializers.ValidationError(
                "A product with this UPC/GTIN already exists.")
        return value

    def validate_price(self, value):
        pattern =r'^\d{1,8}(\.\d{1,2})?$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Price must be a positive number with up to two decimal places.")
        return value 

    def save(self):
        seller = self.context['request'].user.seller
        var = self.validated_data
        var["theme"] = None
        seller.draft_data['tmp'].update({"actual_variations": {1: var}})
        seller.save()
        return var

# loop through keys and use serializer to validate each variation


class OfferWrrapperSerializer(serializers.Serializer):
    variations = serializers.DictField()

    def validate(self, data):
        seller = self.context['request'].user.seller
        Pvar = seller.draft_data['tmp'].get("possible_variation", None)
        if Pvar is None:
            raise serializers.ValidationError(
                "you need to set product variations parameters first")
        var = data["variations"]
        # try and catch clause here in case entered id does not exist in possible variations
        upc_seen = set()
        default_count = 0
        for k , v in var.items():
            if not k.isdigit():
                raise serializers.ValidationError("Keys must be integers.")
            offer_serializer = OfferSerializer(data = v)
            if not offer_serializer.is_valid():
                raise serializers.ValidationError("Invalid data for variation {}: {}".format(k, offer_serializer.errors))
            offer_validated = offer_serializer.validated_data
            if offer_validated["UPC"] in upc_seen:
                raise serializers.ValidationError("Duplicate UPC found: {} at variation {}".format(v["UPC"], k))
            upc_seen.add(offer_validated["UPC"])
            if offer_validated["default"]:
                default_count += 1
            var[k] = offer_validated
            var[k]["theme"] = Pvar[k]["theme"]
        if default_count != 1:
                raise serializers.ValidationError(
                    "Only one variant can be default.")
        seller.draft_data['tmp'].update({"actual_variations": var})
        seller.save()
        data["variations"] = var
        return data


class ProductDescriptionSerializer(serializers.Serializer):
    product_description = serializers.CharField(
        max_length=1000, required=True)
    bullet_points = serializers.ListField(min_length=1, max_length=5,
                                          child=serializers.CharField(max_length=500), required=True)

    def validate_bullet_points(self, value):
        if len(value) > 5:
            raise serializers.ValidationError(
                "You can provide up to 5 bullet points.")
        return value

    def save(self):
        seller = self.context['request'].user.seller
        var = self.validated_data
        try:
            seller.draft_data['tmp']["ProductIdentity"].update(var)
        except:
            raise serializers.ValidationError(
                "You need to set product identity first")
        seller.save()
        data = var
        return data

# to be continued


class ClothesDetailsSerializer(serializers.Serializer):
    size = serializers.CharField(
        max_length=100,)  # array of possible sizes
    color = serializers.CharField(
        max_length=500,)  # array of possible colors
    fit = serializers.CharField(max_length=100)
    material = serializers.CharField(max_length=100)
    neckline = serializers.CharField(max_length=100)
    sleeve_length = serializers.CharField(max_length=100)
    closure_type = serializers.CharField(max_length=100)
    style = serializers.CharField(max_length=100)

    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)
        var = self.context['request'].user.seller.draft_data['tmp']["variations"]
        variations = ["size", "color"]
        for key in variations:
            if key in var:
                self.fields.pop(key)


class MedictDetailsSerializer(serializers.Serializer):
    pack_size = serializers.IntegerField()  
    size = serializers.CharField(max_length=40,required = False)  
    strength = serializers.CharField(max_length=50,required = False)
    age = serializers.CharField(max_length=100)
    generic_name = serializers.CharField(max_length=100,required = False)
    active_ingredients = serializers.ListField(child=serializers.CharField(max_length=100),max_length=10)
    contraindications = serializers.CharField(max_length=500,required = False)
    side_effects = serializers.CharField(max_length=500,required = False)
    precautions = serializers.CharField(max_length=500,required = False)
    interactions = serializers.CharField(max_length=500,required = False)
    storage_conditions = serializers.CharField(max_length=500,required = False)
    expiry_date = serializers.CharField(max_length=20)
    manufacturer = serializers.CharField(max_length=100,required = False)
    regulatory_approval = serializers.CharField(max_length=100,required = False)
    prescription_status = serializers.CharField(max_length = 100,required = False)

    def __init__(self, instance=None, data=..., **kwargs):
        super().__init__(instance, data, **kwargs)
        var = self.context['request'].user.seller.draft_data['tmp']["ProductIdentity"].get(
            "product_variations", None)
        if var is None or var == {}:
            self.fields["dosage_form"] = serializers.ChoiceField(
                choices=DOSAGE_FORM_CHOICES)
        else:
            variations = ["pack_size", "size", "strength", "age"]
            for key in variations:
                if key in var.keys():
                    x = self.fields.pop(key)

    def validate_pack_size(self, value):
        dosage_form = self.initial_data.get("dosage_form")
        if value <= 0:
            raise serializers.ValidationError(
                "Pack size must be a positive integer.")
        if dosage_form in SPECIAL_SOLID:
            if value == 1:
                value = f'{str(value)} {dosage_form}'
            else:
                value = f'{str(value)} {plural_special_solid[dosage_form]}'
        else:
            if value == 1:
                value = f'{str(value)} item'
            else:
                value = f'{str(value)} items'

        return value

    def validate_size(self, value):
        pattern = r'^\d+(\.\d+)?\s(mg|g|kg|mcg|ng|ml|l|liter|fl oz|cc|mL|L|U|mEq|%)$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Invalid size format. Examples: '100 mg', '2 g', '500 U', '3 %'."
            )
        num_part = value.split()[0]
        try:
            num = float(num_part)
            if num <= 0:
                raise serializers.ValidationError(
                    "Size value must be a positive number.")
        except ValueError:
            raise serializers.ValidationError(
                "Size value must be a valid number.")
        return value

    def validate_expiry_date(self, value):
        """
        Validate and convert the expiry_date string into a Python date object.
        Accepts common formats like YYYY-MM-DD or DD/MM/YYYY.
        """
        # Try multiple formats for flexibility
        accepted_formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]

        for fmt in accepted_formats:
            try:
                parsed_date = datetime.strptime(value, fmt).date()
                # Optional: check if expiry date is in the future
                if parsed_date <= datetime.now().date():
                    raise serializers.ValidationError("Expiry date must be in the future.")
                return str(parsed_date)
            except ValueError:
                continue  # try next format

        raise serializers.ValidationError(
            "Invalid date format. Please use YYYY-MM-DD, DD/MM/YYYY, or MM/DD/YYYY."
        )

    def validate_strength(self, value):
        pattern = r'^\d+(\.\d+)?\s(mg|g|kg|mcg|ng|L|mL|cc|U|mEq|%)?$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Invalid strength format. Examples: '100 mg', '2 g', '500 U', '3 %'."
            )
        # Extract the numeric part and check if positive
        num_part = value.split()[0]
        try:
            num = float(num_part)
            if num <= 0:
                raise ValueError
        except (ValueError, IndexError):
            raise serializers.ValidationError(
                "Strength value must be a positive number."
            )
        return value

        # validations then save to draft data

    def validate_age(self, value):
        if value not in AGE_CHOICES:
            try:
                x, y = map(int, value.split('-'))
            except (ValueError, AttributeError):
                raise serializers.ValidationError(
                    "Age range must be in format 'X-Y' (e.g., '10-20').")

            if x >= y:
                raise serializers.ValidationError(
                    "First age (X) must be less than second age (Y).")

            if x < 0 or y > 120:
                raise serializers.ValidationError(
                    "Ages must be between 0 and 120.")
        return value

    def validate(self, data):
        dosage_form = data.get("dosage_form",None)
        if dosage_form is None:
            dosage_form = self.context['request'].user.seller.draft_data['tmp']["ProductIdentity"]["product_details"]["dosage_form"]
        Data = [v for v in [data.get("size"), data.get("strength")] if v is not None]
        for value in Data:
            unit = value.split()[1]
            if dosage_form in LIQUID_FORMS:
                if unit not in VALID_LIQUID_UNITS:
                    raise serializers.ValidationError(
                        f"Invalid unit '{unit}' for liquid dosage form. Valid liquid units: {VALID_LIQUID_UNITS}"
                    )
            elif dosage_form in SOLID_FORMS:
                if unit not in VALID_MASS_UNITS:
                    raise serializers.ValidationError(
                        f"Invalid unit '{unit}' for solid dosage form. Valid mass units: {VALID_MASS_UNITS}"
                    )
        return data

    def save(self):
        seller = self.context['request'].user.seller
        PD = seller.draft_data['tmp']["ProductIdentity"].get("product_details", None)
        if PD is None:
            seller.draft_data['tmp']["ProductIdentity"].update({"product_details": self.validated_data})
        else:
            seller.draft_data['tmp']["ProductIdentity"]["product_details"].update(self.validated_data)
        seller.save()
        return seller.draft_data['tmp']["ProductIdentity"]["product_details"]


class SaveDraftSerializer(serializers.Serializer):
    draft_name = serializers.CharField(max_length=100,required = True)

class PublishDraftSerializer(serializers.Serializer):
    draft_name = serializers.CharField(max_length=100,required = False)
