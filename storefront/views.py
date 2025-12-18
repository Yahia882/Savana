from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, exceptions
from sellers.models import ProductIdentity, Offer
from .serializers import AddToCartSerializer, ProductSerializer, ProductDetailSerializer, ViewCartSerializer, CountUpdateSerializer, CheckoutSerializer, update_cart_price
from rest_framework import permissions
from .models import Cart, Checkout, CheckoutItem
from datetime import timedelta
from django.utils import timezone
import stripe
import datetime
from django.conf import settings


def del_non_existing_offers(instance):
    offer_ids = list(instance.items.keys())
    offers = {str(o.pk): o for o in Offer.objects.filter(pk__in=offer_ids)}
    for item_id in instance.items.keys():
        offer = offers.get(str(item_id))
        if not offer:
            del instance.items[str(item_id)]
            continue
    instance.save(update_fields=['items'])
    return instance


def get_line_items(user):
    line_items = []
    checkout_items = []
    cart = del_non_existing_offers(user.cart)  # cart instane
    offer_ids = list(cart.keys())
    offers = {str(o.pk): o for o in Offer.objects.filter(pk__in=offer_ids)}
    cart_items = cart.items
    for item_id, item_data in cart_items.items():
        offer = offers.get(str(item_id))
        checkout_items.append(
            {"product_identity": item_data["product_identity"],
             "product_variation": item_data["product_variation"],
             "offer": offer.id,
             "store": offer.seller.store.id,
             "name": item_data["theme"],
             "price": offer.price,
             "quantity": item_data["count"],
             "discounted_price": offer.discounted_price,
             }
        )
        line_items.append({"price_data": {
            "currency": "usd",
            "prodcuct": offer.PV.product_identity.stripe_product_id,
            "tax_behavior": "exclusive",
            "unit_amount_decimal": offer.price,
        },
            "quantity": item_data["count"],
            "meta_data": {"offer_id": offer.id}
        },
        )
    return line_items, checkout_items


def get_shipping_cost(user):
    address = user.addresses.get(default=True)
    # calculate cost based on address (dynamic shipping cost)
    # logic here
    # in the mean time we will have fixed delivery cost
    shipping_cost = 1000

    shipping_options = [
        {
            'shipping_rate_data': {
                'display_name': 'standard delivery',
                'type': 'fixed_amount',
                'fixed_amount': {
                    'amount': shipping_cost,
                    'currency': 'usd',
                },
                # Crucial for tax calculation:
                'tax_code': 'txcd_92010001',
                'tax_behavior': 'exclusive',
            },
        },
    ],
    shipping_address_collection = {
        'allowed_countries': ['US'],
    },
    return shipping_options, shipping_address_collection


def update_customer_address(user):
    default_address = user.addresses.get(default=True)
    customer = stripe.Customer.modify(
        user.customer.customer_id,
        address={
            # Required for calculating tax
            "country": default_address["country"],
            "state": default_address["state"],
            "city": default_address["city"],
            "line1": default_address["street_address"],
            "line2": f'{default_address["building_address"]}, {default_address["apartment_address"]}',
            # Required for calculating tax
            "postal_code": default_address["postal_code"]
        }

    )


def get_timestamp(minutes):
    duration = datetime.timedelta(minutes=minutes)
    time_now_utc = datetime.datetime.now(datetime.timezone.utc)
    return time_now_utc + duration


def create_checkout_instance(user, session, line_items, checkout_items):
    now = timezone.now()
    checkout_instance = Checkout.objects.create(
        user=user,
        subtotal=session["amount_subtotal"],
        expires_at=now + timedelta(minutes=settings.checkout_expiration),
        soft_expires_at=now + timedelta(days=1),
        payment_session_id=session.id
    )
    for checkout_item in checkout_items:
        CheckoutItem.objects.create(
            checkout=checkout_instance,
            product_identity=checkout_item["product_identity"],
            product_variation=checkout_item["product_variation"],
            offer=checkout_item["offer"],
            store=checkout_item["store"],
            name=checkout_item["name"],
            price=checkout_item["price"],
            discounted_price=checkout_item["discounted_price"],
        )
    items = checkout_instance.items.all()
    # this need to be refactored, it's very bad performance wise
    for item in line_items:
        instance = items.get(offer=item["meta_data"]["offer_id"])
        instance.line_item_id = item["data"]["id"]
        instance.save()
# whatever has # sign will be assigned after the checkout session is completed

    return checkout_instance


class ProductGetListView(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, **kwargs):
        if kwargs.get("pk"):
            product = ProductIdentity.objects.get(
                status="approved", id=kwargs["pk"])
            serializer = ProductDetailSerializer(product)
            return Response(serializer.data)
        else:
            products = ProductIdentity.objects.filter(status="approved")
            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data)


class AddToCartView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddToCartSerializer

    def post(self, request, format=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get(self, request, format=None):
        try:
            instance = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response({"detail": "Cart is empty."},)
        serializer = ViewCartSerializer(instance)
        return Response(serializer.data)

    def put(self, request, format=None):
        serializer = CountUpdateSerializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        instance = Cart.objects.get(user=request.user)
        serializer = ViewCartSerializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        cart = Cart.objects.get(user=request.user)
        cart.items = {}
        cart.save()
        return Response({"detail": "Cart cleared."}, status=status.HTTP_200_OK)


class CheckoutView(APIView):

    def post(self, request):
        user = request.user
        instance = Checkout.objects.get(user=user, status="pending").exists()
        if instance.exists():
            instance.status = "abandoned"
            instance.save()

        time_stamp = get_timestamp(settings.checkout_expiration)
        update_customer_address(user)
        line_items, checkout_items = get_line_items(user)
        shipping_options, shipping_address_collection = get_shipping_cost(user)
        session = stripe.checkout.Session.create(
            automatic_tax={"enabled": True},
            customer=user.customer.customer_id,
            line_items=line_items,
            mode="payment",
            ui_mode="embedded",
            return_url="https://example.com/return",
            saved_payment_method_options={"payment_method_save": "enabled"},
            shipping_options=shipping_options,
            shipping_address_collection=shipping_address_collection,
            expires_at=time_stamp,
            allow_promotion_codes=True,
        )
        line_items_stripe = stripe.checkout.Session.list_line_items(
            session.id,
            limit=100
        ).data
        checkout_instance = create_checkout_instance(
            user, session, line_items_stripe, checkout_items)
        # would you return the checkout instance
        # if yes then you need serializer for checkout instance with checkout items
        return Response({"clientSecret": session.client_secret, "Checkout": CheckoutSerializer(checkout_instance).data}, status=status.HTTP_200_OK)
