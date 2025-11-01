from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView, get_object_or_404
from rest_framework.permissions import AllowAny
import stripe
from rest_framework import permissions
from django.core.exceptions import ObjectDoesNotExist
from decouple import config
from django.conf import settings
from .tokens import CustomizedTokenObtainPairSerializer
from dj_rest_auth.views import LoginView
from .jwt_auth import SellerJWTCookieAuthentication
import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Offer, ProductVariation, Seller, SellerProduct, Store, ProductIdentity
from users.models import Customer, PaymentMethod
from .serializers import ClothesDetailsSerializer, LocationSerializer, MedictDetailsSerializer, OfferSerializer, OfferWrrapperSerializer, ProductDescriptionSerializer,PublishDraftSerializer, SaveDraftSerializer
from dj_rest_auth.app_settings import api_settings as rest_auth_api_settings
from rest_framework import status
from .serializers import CustomizedJWTSerializer, StoreInfoSerializer, VerifySellerSerializer, GetSellerSerializer, ProductIdentitySerializer, ClothesVariationSerializer, MedicalVariationSerializer
from .permissions import HasEmail, HasNoVariations, HasVariations, IsSeller, CanVerify, ProductInfoCollected
from .generics import UpdateCreateAPIView, ListRetrieveUpdate
from rest_framework.exceptions import ValidationError
# Create your views here.
stripe.api_key = settings.STRIPE_TEST_SECRET_KEY


@method_decorator(csrf_exempt, name='dispatch')
class onboarding(APIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasEmail]

    def post(self, request):
        user = request.user
        try:
            seller = user.seller
            seller_id = seller.seller_id
        except ObjectDoesNotExist:
            try:
                acc = stripe.Account.create(
                    # country = user.country,
                    email=user.email,
                    controller={
                        "stripe_dashboard": {
                            "type": "express",
                        },
                        "fees": {
                            # when you tax the merchant consider 2$ per active user and .25% + 25 cents per transaction
                            "payer": "application"
                            # + normal tax on the products + payment processing fee
                        },
                        "losses": {
                            # prevent user being in debt if u can, through preventing payouts till after a month
                            "payments": "application"
                        },
                    },
                )
                seller_id = acc["id"]
                seller = Seller.objects.create(
                    user=user,
                    seller_id=seller_id,
                )
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            account_session = stripe.AccountSession.create(
                account=seller_id,
                components={
                    "account_onboarding": {"enabled": True},
                },
            )
        except Exception as e:
            print(e)
        return Response({
            'client_secret': account_session.client_secret,
        })

# clean the redundant code later


@method_decorator(csrf_exempt, name='dispatch')
class sellerPaymentMethod (APIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsSeller, HasEmail]

    def put(self, request):
        user = request.user
        if not user.seller.status["onboard"]:
            return Response({"error": "finish onboarding first"}, status=status.HTTP_400_BAD_REQUEST)
        if not user.seller.PG_verified:
            return Response({"error": "you cannot update payment method because you are not verified yet"}, status=status.HTTP_400_BAD_REQUEST)

        customer_id = user.customer.customer_id
        customer_session = stripe.CustomerSession.create(
            customer=customer_id,
            components={
                "payment_element": {
                    "enabled": True,
                    "features": {
                        "payment_method_redisplay": "enabled",
                        "payment_method_save": "enabled",
                        "payment_method_save_usage": "off_session",
                        "payment_method_remove": "enabled",
                    },
                },
            },
        )
        intent = stripe.SetupIntent.create(
            customer=customer_id,
        )

        return Response({
            'customer_session_client_secret': customer_session.client_secret, 'intent_client_secret': intent.client_secret
        })

    def post(self, request):
        user = request.user
        if not user.seller.status["onboard"]:
            return Response({"error": "finish onboarding first"}, status=status.HTTP_400_BAD_REQUEST)
        if user.seller.status["store_pm"]:
            return Response({"error": "payment method already been set"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            customer = user.customer
            customer_id = customer.customer_id
        except Exception:
            customer = stripe.Customer.create(
                email=user.email,
            )
            customer_id = customer["id"]
            # refactor the code later for example make sure the database accessing is optimal and performe well
            Customer.objects.create(
                user=user,
                customer_id=customer_id,
            )
        customer_session = stripe.CustomerSession.create(
            customer=customer_id,
            components={
                "payment_element": {
                    "enabled": True,
                    "features": {
                        "payment_method_redisplay": "enabled",
                        "payment_method_save": "enabled",
                        "payment_method_save_usage": "off_session",
                        "payment_method_remove": "enabled",
                    },
                },
            },
        )
        intent = stripe.SetupIntent.create(
            customer=customer_id,
        )

        return Response({
            'customer_session_client_secret': customer_session.client_secret, 'intent_client_secret': intent.client_secret
        })
# maybe add update also (put request)


class StoreInfo(UpdateCreateAPIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasEmail]
    serializer_class = StoreInfoSerializer

    def get_object(self):
        instance = Store.objects.get(seller=self.request.user.seller)
        return instance

    def create(self, request, *args, **kwargs):
        if not request.user.seller.status["store_pm"]:
            return Response({"error": "finish setting your payment method first"}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.seller.status["store_info"]:
            return Response({"error": "store info already been set"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        seller = self.request.user.seller
        serializer.save()
        account = stripe.Account.retrieve(seller.seller_id)
        seller.location = account["country"]
        seller.status["store_info"] = True
        seller.save()


class test_Onboarding(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        account = stripe.Account.retrieve("acct_1QLPvnQ1FTbZXKMh")
        external_accounts = account.external_accounts
        return Response({"external accounts": external_accounts})

    def post(self, request, *args, **kwargs):
        acc = stripe.Account.create(
            email="andsohespoke0@gmail.com",
            controller={
                "stripe_dashboard": {
                    "type": "express",
                },
                "fees": {
                    "payer": "application"
                },
                "losses": {
                    "payments": "application"
                },
            },
        )
        try:
            account_session = stripe.AccountSession.create(
                account=acc["id"],
                # account="acct_1QLPvnQ1FTbZXKMh",
                components={
                    "account_onboarding": {"enabled": True},
                },
            )
        except Exception as e:
            print(e)
        return Response({
            'client_secret': account_session.client_secret,
        })


class test_account_management(APIView):
    def post(self, request, *args, **kwargs):

        try:
            account_session = stripe.AccountSession.create(
                account="acct_1QLPvnQ1FTbZXKMh",
                components={
                    "account_management": {"enabled": True},
                },
            )
        except Exception as e:
            print(e)
        return Response({
            'client_secret': account_session.client_secret,
        })


class test_notification_banner(APIView):
    def post(self, request):
        account_session = stripe.AccountSession.create(
            account='acct_1QLnJNPxFPhF2bZ9',
            components={
                "notification_banner": {
                    "enabled": True,
                    "features": {"external_account_collection": True},
                },
            },
        )
        return Response({'client_secret': account_session.client_secret, })


# if you are using third party auth like google or facebook you login normally as a customer and then change password (optionaly)
# if you don't have an email and you use a phone number, you have to update your account info and add an email to your account (mandatory)

# you can add two way authentication to the view through authenticate the user in this view (do not send token) after the user
# authenticates successfully, send OTP to the user's email or phone number, then create other view to enter the OTP and verify it
# if the OTP is correct, create the token and send it to the user
@method_decorator(csrf_exempt, name='dispatch')
class signup(LoginView):
    permission_classes = [permissions.IsAuthenticated, HasEmail]
    serializer_class = None

    def get_response(self, usr_status):

        data = {
            'user': self.user,
            'access': self.access_token,
            "refresh": self.refresh_token,
            "status": usr_status,
        }

        serializer = CustomizedJWTSerializer(
            instance=data,
            context=self.get_serializer_context(),
        )

        response = Response(serializer.data, status=status.HTTP_200_OK)
        if rest_auth_api_settings.USE_JWT:
            from dj_rest_auth.jwt_auth import set_jwt_cookies
            set_jwt_cookies(response, self.access_token, self.refresh_token)
        return response

    def post(self, request, *args, **kwargs):
        self.user = request.user
        self.refresh_token = CustomizedTokenObtainPairSerializer.get_token(
            user=self.user, role="seller")
        self.access_token = self.refresh_token.access_token

        try:
            seller = request.user.seller
        except ObjectDoesNotExist:
            return self.get_response("location")
        for key, value in seller.status.items():
            if value == False:
                return self.get_response(key)
        if seller.app_verified == False or seller.PG_verified == False:
            return self.get_response("not verified")

        return self.get_response("verified")


class login(APIView):
    pass


class SellerHomePage(GenericAPIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    pass


class location(GenericAPIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasEmail]
    serializer_class = LocationSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        allowed = serializer.context["allowed"]
        if allowed:
            return Response({"platform": "stripe"})
        return Response({"platform": "country not supported yet"})


@csrf_exempt        # implement the logic after returning the response through using Celery or any other task queue
def connected_acc_webhook_view(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_CONNECTED_SECRET_KEY
        )
    except ValueError as e:
        # Invalid payload
        print('Error parsing payload: {}'.format(str(e)))
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print('Error verifying webhook signature: {}'.format(str(e)))
        return HttpResponse(status=400)

    # Handle the event
    if event.type == 'account.updated':
        account = event.data.object
        # Occurs whenever an account status or property has changed
        print('account property changed {}'.format(event.type))
        if account["charges_enabled"] == True and account["payouts_enabled"] == True:
            acc = Seller.objects.get(seller_id=account["id"])
            acc.PG_verified = True
            acc.status["onboard"] = True
            acc.save()
            print('stripe_verified is true')
        elif account["details_submitted"] == True and account["future_requirements"]["past_due"] == []:
            acc = Seller.objects.get(seller_id=account["id"])
            acc.status["onboard"] = True
            acc.save()
            print('onboard is true')

        elif account["details_submitted"] == False or account["future_requirements"]["past_due"] is not None:
            acc = Seller.objects.get(seller_id=account["id"])
            acc.status["onboard"] = False
            acc.PG_verified = False
            acc.save()
            print('onboard is false')

    else:
        print('Unhandled event type {}'.format(event.type))

    return HttpResponse(status=200)


@csrf_exempt        # implement the logic after returning the response through using Celery or any other task queue
def account_webhook_view(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_PLATFORM_SECRET_KEY
        )
    except ValueError as e:
        # Invalid payload
        print('Error parsing payload: {}'.format(str(e)))
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print('Error verifying webhook signature: {}'.format(str(e)))
        return HttpResponse(status=400)

    # Handle the event
    if event.type == 'setup_intent.succeeded':
        setup_intent = event.data.object
        customer_id = setup_intent["customer"]
        customer_instance = Customer.objects.get(customer_id=customer_id)
        user = customer_instance.user
        pm_id = setup_intent["payment_method"]
        pm_obj = stripe.Customer.retrieve_payment_method(
            customer_id,
            pm_id,
        )
        pm = PaymentMethod.objects.create(
            Payment_method_id=pm_obj["id"],
            card_brand=pm_obj["card"]["brand"],
            funding=pm_obj["card"]["funding"],
            last4=pm_obj["card"]["last4"],
            exp_month=pm_obj["card"]["exp_month"],
            exp_year=pm_obj["card"]["exp_year"],
            customer=customer_instance
        )
        acc = Seller.objects.get(user=user)
        acc.pm_sub = pm
        acc.status["store_pm"] = True
        acc.save()

    elif event.type == 'payment_method.attached':
        payment_method = event.data.object  # contains a stripe.PaymentMethod
        print('PaymentMethod was attached to a Customer!')
    # ... handle other event types
    else:
        print('Unhandled event type {}'.format(event.type))

    return HttpResponse(status=200)


@method_decorator(csrf_exempt, name='dispatch')
class VerifySeller(ListRetrieveUpdate):
    serializer_class = VerifySellerSerializer
    permission_classes = [CanVerify,]

    def get_serializer_class(self):
        if self.request.method == "GET" and self.kwargs.get('pk'):
            return GetSellerSerializer
        else:
            return VerifySellerSerializer

    def get_queryset(self):
        queryset = Seller.objects.filter(
            PG_verified=True,
            app_verified=False,
            status__store_info=True
        )
        return queryset

# the process creating a product


class ProductIdentityView(GenericAPIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductIdentitySerializer

    def get(self, request):
        seller = request.user.seller
        try:
            PI = seller.draft_data['tmp'].get("ProductIdentity", {})
            return Response(PI)
        except:
            return Response({}, status=204)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


CLOTHES = ['clothes', 'tshirt', 'shoes', 'sports_clothes', 'sports_shoes',]
MEDICAL = ['medicines', 'medical_equipment', 'medical_supplies',
           'medical_devices', 'medical_instruments']


class VariationParameters(APIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasVariations]

    def get_serializer_class(self):
        product_type = self.request.user.seller.draft_data['tmp']["ProductIdentity"]["product_type"]
        if product_type in CLOTHES:
            return ClothesVariationSerializer
        elif product_type in MEDICAL:
            return MedicalVariationSerializer
        else:
            return Response({"error": "product type not supported"}, status=400)

    def get(self, request):
        pv = request.user.seller.draft_data["tmp"]["ProductIdentity"].get(
            "product_variations", None)
        if pv is not None:
            return Response(pv)
        fields = self.get_serializer_class().get_fields()
        schema = {}
        for name, field in fields.items():
            field_info = {"type": str(field.__class__.__name__)}
            if hasattr(field, "choices") and field.choices:
                field_info["choices"] = list(field.choices.keys())
            schema[name] = field_info
        return Response(schema)

    def post(self, request):
        serializer_class = self.get_serializer_class()
        if serializer_class is None:
            return Response({"error": "product type not supported"}, status=400)
        serializer = serializer_class(
            data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data)


class OneProductOffer(GenericAPIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasNoVariations]
    serializer_class = OfferSerializer

    def get(self, request):
        var = request.user.seller.draft_data["tmp"].get(
            "actual_variations", None)
        if var:
            return Response(var["1"])
        else:
            print("debug")
            return Response({})

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data)


class VariationsOffer(GenericAPIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasVariations]
    serializer_class = OfferWrrapperSerializer

    def get(self, request):
        var = request.user.seller.draft_data["tmp"].get(
            "actual_variations", None)
        if var is not None:
            return Response(var)
        else:
            return Response({}, status=204)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class ProductDescription(GenericAPIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductDescriptionSerializer

    def get(self, request):
        PI = request.user.seller.draft_data['tmp']["ProductIdentity"]
        if PI.get("product_description", None) is not None:
            return Response({"product_description": PI["product_description"], "bullet_points": PI["bullet_points"]})
        else:
            return Response({})

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data)


class ProductDetails(GenericAPIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated,]

    def get_serializer_class(self):
        try:
            PI = self.request.user.seller.draft_data['tmp']["ProductIdentity"]
            if PI["has_variations"] and not PI.get("product_variations", None):
                return ValidationError({"error": "set variation first"})
        except Exception:
            raise ValidationError({"error": "set product identity first"})
        if PI["product_type"] in CLOTHES:
            return ClothesDetailsSerializer
        elif PI["product_type"] in MEDICAL:
            return MedictDetailsSerializer
        else:
            raise ValidationError({"error": "product type not supported"})

    def get(self, request):
        serializer_class = self.get_serializer()
        PI = self.request.user.seller.draft_data['tmp']["ProductIdentity"]
        if PI.get("product_details", {}) .get("active_ingredients") is not None:
            return Response(PI["product_details"])
        fields = serializer_class.fields
        schema = {}
        for name, field in fields.items():
            field_info = {"type": str(field.__class__.__name__)}
            if hasattr(field, "choices") and field.choices:
                field_info["choices"] = list(field.choices.keys())
            schema[name] = field_info
        return Response(schema)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()
        return Response(data)

def save_to_db(seller, data):
    PI = ProductIdentity.objects.create(**data["ProductIdentity"])
    SellerProduct.objects.create(
            seller=seller,
            product_identity=PI,
            variations=data["ProductIdentity"].get("product_variations", {}),
            default = True,
        )
    variations = data["actual_variations"]
    for k in variations.keys():
        PV = ProductVariation.objects.create(
            product_identity=PI,
            upc=variations[k]["UPC"],
            theme=variations[k]["theme"],
            default=variations[k].get("default", False)
        )
        Offer.objects.create(
            sku=variations[k]["sku"],
            price=variations[k]["price"],
            stock=variations[k]["stock"],
            PV=PV,
            seller=seller,
            fullfillment_channel=variations[k]["fullfilled_by"],
            condition=variations[k]["condition"],
        )
        PI.status = "pending"
        PI.save()
        

class PublishProduct(GenericAPIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated, ProductInfoCollected]
    serializer_class = PublishDraftSerializer

    def post(self, request):
        seller = request.user.seller
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        draft_name = serializer.validated_data.get('draft_name', None)
        tmp_data = seller.draft_data.get("tmp", {})
        if draft_name and tmp_data:
            return Response({"error": "no product to publish please re-enter product info"}, status=400)
        if draft_name:
            data = seller.draft_data.get("draft_products", {}).get(draft_name, None)
            if data is None:
                return Response({"error": f"draft name {draft_name} does not exist"}, status=400)
            save_to_db(seller , data)
            seller.draft_data["draft_products"].pop(draft_name)
            seller.save()
            return Response({"message": f" product will get reviewed soon, we will notify you when the product is approved and published"})
        else:
            data = tmp_data
            save_to_db(seller,data)
            seller.draft_data["tmp"] = {}
            seller.save()
            return Response({"message": f" product will get reviewed soon, we will notify you when the product is approved and published"})


class SaveDraft(GenericAPIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated, ProductInfoCollected]
    serializer_class = SaveDraftSerializer

    def get_permissions(self):
        permission_classes = []
        if self.request.method == "POST":
            permission_classes = [permissions.IsAuthenticated, ProductInfoCollected]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get(self, request, *args, **kwargs):
        seller = request.user.seller
        if kwargs.get('pk', None):
            data = seller.draft_data.get(
                "draft_products", {}).get(kwargs['pk'], None)
            return Response(data)
        drafts = seller.draft_data.get("draft_products", {})
        draft_names = []
        for draft_name in drafts.keys():
            draft_names.append(draft_name)
        return Response(draft_names)

    def post(self, request):
        seller = request.user.seller    
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        draft_name = serializer.validated_data['draft_name']
        if seller.draft_data.get("draft_products", None) is None:
            seller.draft_data["draft_products"] = {
                draft_name: seller.draft_data["tmp"]}
        else:
            if draft_name.lower() in (k.lower() for k in seller.draft_data["draft_products"].keys()):
                return Response({"error": "draft name {} already exists".format(draft_name)}, status=400)
            seller.draft_data["draft_products"][draft_name] = seller.draft_data["tmp"]
        seller.draft_data["tmp"] = {}
        seller.save()
        return Response({"message": f"draft {draft_name} saved successfully"})
