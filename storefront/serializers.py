from rest_framework import serializers
from sellers.models import Offer, ProductIdentity, ProductVariation, SellerProduct
from .models import Cart
from rest_framework.exceptions import ValidationError

class ProductSerializer(serializers.ModelSerializer):
    offer = serializers.SerializerMethodField()
    default_theme = serializers.SerializerMethodField()
    class Meta:
        model = ProductIdentity
        fields = ["id","default_theme","offer", "item_name", "product_variations", "brand_name",]
    
    def get_offer(self,obj):
        # default seller
        sell = obj.sellers.get(default=True) 
        # default variations
        var = None
        if obj.has_variations:
            var = obj.variations.get(default=True)
        else:
            var = obj.variations.first()
        # Offer
        offer = var.offers.get(seller = sell.seller,PV = var)
        return {"id":offer.id,"price": offer.price, "stock":offer.stock, "store": sell.seller.store.name}

    def get_default_theme(self,obj):
        if obj.has_variations:
            var = obj.variations.get(default=True)
            return var.theme
        return None

class OfferSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='seller.store.name', read_only=True)
    default = serializers.SerializerMethodField()
    class Meta:
        model = Offer
        fields = ["id","price", "stock", "seller","store_name","default"]

    def get_default(self, obj):
        instance = obj.PV.product_identity.sellers.get(seller = obj.seller)
        return instance.default


class ProductVariationSerializer(serializers.ModelSerializer):
    offers = OfferSerializer(many=True,read_only=True)
    class Meta:
        model = ProductVariation
        fields = ["theme", "default", "offers"]

class SellerProductSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='seller.store.name', read_only=True)
    class Meta:
        model = SellerProduct
        fields = ["seller","variations","store_name"]

class ProductDetailSerializer(serializers.ModelSerializer):
    variations = ProductVariationSerializer(many=True,read_only=True)
    default_seller = serializers.SerializerMethodField(source='sellers', read_only=True)
    class Meta:
        model = ProductIdentity
        fields = ["item_name", "product_type", "brand_name", "product_description",
                  "bullet_points", "product_details","product_variations", "variations","default_seller"]
    def get_default_seller(self,obj):
        instance = obj.sellers.get(default=True)
        return SellerProductSerializer(instance).data
    


class AddToCartSerializer(serializers.Serializer):
    add_item = serializers.ListField(
        child=serializers.IntegerField(), write_only=True)
    items = serializers.DictField(read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        updated_items = {}
        subtotal = 0
        for item_id, item_data in instance["items"].items():
            try:
                price = Offer.objects.get(pk=item_id).price
            except Offer.DoesNotExist:
                price = 0
            item_data['price'] = price
            count = item_data.get("count", 1)
            subtotal += price * count
            updated_items[item_id] = item_data
        data['items'] = updated_items
        data['subtotal_price'] = subtotal
        return data

    def validate(self, data):   # storing the item details in the cart of the new items
        new_items = {}          # added
        items = data.pop("add_item")
        for k in items:
            item_data = {"count": 1}
            offer = Offer.objects.get(pk=k)
            item_data["theme"] = offer.PV.theme
            item_data["item_name"] = offer.PV.product_identity.item_name
            item_data["store"] = offer.seller.store.name
            new_items[k] = item_data
        data["items"] = new_items
        return data

    def save(self):   # add and save the new items to the cart and get subtotal
        user = self.context['request'].user
        instance, created = Cart.objects.get_or_create(user=user)
        if created:
            instance.items = self.validated_data['items']
        instance.items.update(self.validated_data['items'])
        instance.save()


class ViewCartSerializer(serializers.ModelSerializer):
    items = serializers.DictField(read_only=True)
    class Meta:
        model = Cart
        fields = ['items']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        updated_items = {}
        subtotal = 0
        for item_id, item_data in instance.items.items():
            try:
                price = Offer.objects.get(pk=item_id).price
            except Offer.DoesNotExist:
                price = 0
                raise ValidationError(f"Offer with id {item_id} does not exist.")    
            item_data['price'] = price
            count = item_data.get("count", 1)
            subtotal += price * count
            updated_items[item_id] = item_data
        data['items'] = updated_items
        data['subtotal_price'] = subtotal
        return data


class CountUpdateSerializer(serializers.Serializer):
    increment = serializers.IntegerField(required=False)
    decrement = serializers.IntegerField(required=False)
    remove = serializers.IntegerField(required=False)

    def validate(self, data):
        user = self.context["request"].user
        instance = Cart.objects.get(user=user)
        items = instance.items
        increment = data.get("increment")
        decrement = data.get("decrement")
        remove = data.get("remove")

        actions = [increment,decrement,remove]
        used = [a for a in actions if a is not None]
        if len(used) != 1:
            raise serializers.ValidationError("You must provide exactly one of increment, decrement, or remove.")
        
        if increment:
            items[f"{increment}"]["count"] += 1
        elif decrement:
            if items[f"{decrement}"]["count"] > 1:
                items[f"{decrement}"]["count"] -= 1
            elif items[f"{decrement}"]["count"] == 1:
                items.pop(f"{decrement}")
        elif remove:
            items.pop(f"{remove}")
        instance.items = items
        instance.save()
        return data

