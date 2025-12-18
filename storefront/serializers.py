from rest_framework import serializers
from sellers.models import Offer, ProductIdentity, ProductVariation, SellerProduct
from .models import Cart, Checkout, CheckoutItem
from rest_framework.exceptions import ValidationError


class ProductSerializer(serializers.ModelSerializer):
    offer = serializers.SerializerMethodField()
    default_theme = serializers.SerializerMethodField()

    class Meta:
        model = ProductIdentity
        fields = ["id", "default_theme", "offer",
                  "item_name", "product_variations", "brand_name",]

    def get_offer(self, obj):
        # default seller
        sell = obj.sellers.get(default=True)
        # default variations
        var = None
        if obj.has_variations:
            var = obj.variations.get(default=True)
        else:
            var = obj.variations.first()
        # Offer
        offer = var.offers.get(seller=sell.seller, PV=var)
        return {"id": offer.id, "price": offer.price, "stock": offer.stock, "store": sell.seller.store.name}

    def get_default_theme(self, obj):
        if obj.has_variations:
            var = obj.variations.get(default=True)
            return var.theme
        return None


class OfferSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(
        source='seller.store.name', read_only=True)
    default = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = ["id", "price", "stock", "seller", "store_name", "default"]

    def get_default(self, obj):
        instance = obj.PV.product_identity.sellers.get(seller=obj.seller)
        return instance.default


class ProductVariationSerializer(serializers.ModelSerializer):
    offers = OfferSerializer(many=True, read_only=True)

    class Meta:
        model = ProductVariation
        fields = ["theme", "default", "offers"]


class SellerProductSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(
        source='seller.store.name', read_only=True)

    class Meta:
        model = SellerProduct
        fields = ["seller", "variations", "store_name"]


class ProductDetailSerializer(serializers.ModelSerializer):
    variations = ProductVariationSerializer(many=True, read_only=True)
    default_seller = serializers.SerializerMethodField(
        source='sellers', read_only=True)

    class Meta:
        model = ProductIdentity
        fields = ["item_name", "product_type", "brand_name", "product_description",
                  "bullet_points", "product_details", "product_variations", "variations", "default_seller"]

    def get_default_seller(self, obj):
        instance = obj.sellers.get(default=True)
        return SellerProductSerializer(instance).data


def update_cart_price(instance):
    updated_items = {}
    subtotal = 0
    offer_ids = list(instance.keys())
    offers = {str(o.pk): o for o in Offer.objects.filter(pk__in=offer_ids)}

    # this is incorrect intance is cart instance not dictionary
    for item_id, item_data in instance.items.items():
        offer = offers.get(str(item_id))
        if not offer:
            continue
        item_data['price'] = offer.price
        count = item_data.get("count", 1)
        subtotal += offer.price * count
        updated_items[item_id] = item_data
    return updated_items, subtotal


def del_non_existing_offers(user):
    instance, created = Cart.objects.get_or_create(user=user)
    if instance.items not in [{}, None]:
        offer_ids = list(instance.items.keys())
        offers = {str(o.pk): o for o in Offer.objects.filter(pk__in=offer_ids)}
        for item_id in instance.items.keys():
            offer = offers.get(str(item_id))
            if not offer:
                del instance.items[str(item_id)]
                continue
    return instance

# you delete non existing offers from cart and update the cart price
# create a request to do that as well without necessarily adding or removing items
# just when the user views the cart create a post request to update the cart price and delete non existing offers
# neccesary addition that you have to update the cart instance whenever the user views the cart
# post request to update the cart instance then return the updated instance


class AddToCartSerializer(serializers.Serializer):
    add_item = serializers.ListField(
        child=serializers.IntegerField(), write_only=True)
    items = serializers.DictField(read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['items'], data['subtotal_price'] = update_cart_price(instance)
        return data

    def validate(self, data):   # storing the item details in the cart of the new items added
        user = self.context['request'].user
        instance = del_non_existing_offers(user)
        new_items = {}
        items = data.pop("add_item")
        for k in items:
            item_data = {"count": 1}
            offer = Offer.objects.get(pk=k)
            item_data["product_identity"] = offer.PV.product_identity.id
            item_data["product_variation"] = offer.PV.id
            item_data["theme"] = offer.PV.theme
            item_data["item_name"] = offer.PV.product_identity.item_name
            item_data["store"] = offer.seller.store.name
            new_items[k] = item_data
        data["items"] = new_items
        instance.items.update(new_items)
        instance.save(update_fields=['items'])
        self.instance = instance
        return data


class ViewCartSerializer(serializers.ModelSerializer):
    items = serializers.DictField(read_only=True)

    class Meta:
        model = Cart
        fields = ['items']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['items'], data['subtotal_price'] = update_cart_price(instance)
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

        actions = [increment, decrement, remove]
        used = [a for a in actions if a is not None]
        if len(used) != 1:
            raise serializers.ValidationError(
                "You must provide exactly one of increment, decrement, or remove.")

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


class CheckoutItemSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    img = serializers.URLField(source='product_variation.image', read_only=True)
    subtotal = serializers.SerializerMethodField()
    class Meta:
        model = CheckoutItem
        fields = ["store", "name", "price", "quantity",
                  "discounted_price","img","subtotal"]

    def get_name(self, obj):
        if obj.product_variation.theme not in [None, {}]:
            return f'{obj.product_identity.item_name} {obj.product_variation.theme}'
        return obj.product_identity.item_name
    def get_price(self, obj):
        return obj.price * obj.quantity


class CheckoutSerializer(serializers.ModelSerializer):
    items = CheckoutItemSerializer(many=True, read_only=True)

    class Meta:
        model = Checkout
        fields = ["subtotal","items"]

