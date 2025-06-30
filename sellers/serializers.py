from rest_framework import serializers
from django_countries.serializer_fields import CountryField
from .models import Store , Seller
from users.models import PaymentMethod
from django_countries.serializers import CountryFieldMixin
from dj_rest_auth.app_settings import api_settings
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

        user_data = JWTUserDetailsSerializer(obj['user'], context=self.context).data
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
    store_name = serializers.CharField(max_length=100)
    seller = serializers.CharField(source = "seller.id",read_only= True)
    class Meta:
        model = Store
        fields = ["seller",'store_name']
    def validate_store_name(self, value):
        if Store.objects.filter(name=value).exists():
            raise serializers.ValidationError("A store with this name already exists.")
        return value
    def create(self,validated_data):
        seller = self.context['request'].user.seller
        instance = Store.objects.create(name=validated_data['store_name'],seller=seller)
        return instance


class VerifySellerSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    PG_verified = serializers.BooleanField(read_only=True)
    store_name = serializers.CharField(source='Seller.store.name', read_only=True)
    location = serializers.CharField(read_only=True)
    class Meta:
        model = Seller
        fields = ['id','location', 'PG_verified', 'app_verified']

class PaymentMethodSerializer(serializers.ModelSerializer):

    class Meta:
        model = PaymentMethod
        fields = ["__all__"]


class GetSellerSerializer(CountryFieldMixin,serializers.ModelSerializer):
    store_name = serializers.CharField(source='Seller.store.name')
    payment_method = PaymentMethodSerializer(source='pm_sub',) 
    class Meta:
        model = Seller
        fields = ["__all__"]


