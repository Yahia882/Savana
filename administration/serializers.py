from rest_framework import serializers
from sellers.models import Seller,ProductIdentity, Offer, ProductVariation


class ReviewPublishedProductsSerializer(serializers.ModelSerializer):
   

    class Meta:
        model = ProductIdentity
        fields = ["status"]

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductIdentity
        fields = ["id", "item_name", "has_variations", "brand_name","status"]


class OfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offer
        fields = ["price", "stock", "seller"]


class ProductVariationSerializer(serializers.ModelSerializer):
    offers = OfferSerializer(many=True,read_only=True)
    class Meta:
        model = ProductVariation
        fields = ["theme", "default", "offers"]


class ProductDetailSerializer(serializers.ModelSerializer):
    variations = ProductVariationSerializer(many=True,read_only=True)

    class Meta:
        model = ProductIdentity
        fields = ["item_name", "product_type", "brand_name", "product_description",
                  "bullet_points", "product_details","product_variations", "variations"]
    
