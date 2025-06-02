from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
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
from .models import Seller
from users.models import Customer, PaymentMethod
from .serializers import LocationSerializer
from dj_rest_auth.app_settings import api_settings as rest_auth_api_settings
from rest_framework import status
from .serializers import CustomizedJWTSerializer
from .permissions import HasEmail, IsSeller
# Create your views here.
stripe.api_key = settings.STRIPE_TEST_SECRET_KEY

# acc = stripe.Account.create(
#     email = "yahia.abdo2002@gmail.com",
#     controller={
#     "stripe_dashboard": {
#       "type": "express",
#     },
#     "fees": {
#       "payer": "application"
#     },
#     "losses": {
#       "payments": "application"
#     },
#   },
# )

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

@method_decorator(csrf_exempt, name='dispatch')
class sellerPaymentMethod (APIView):
    authentication_classes = [SellerJWTCookieAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsSeller, HasEmail]

    def post(self, request):
        user = request.user
        if not user.seller.status["onboard"]:
            return Response({"error": "finish onboarding first"}, status=status.HTTP_400_BAD_REQUEST)
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
        if seller.app_verified == False or seller.stripe_verified == False:
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
def my_webhook_view(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        print(settings.STRIPE_WEBHOOK_SECRET_KEY)
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET_KEY
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
            acc.stripe_verified = True
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
            acc.stripe_verified = False
            acc.save()
            print('onboard is false')

    elif event.type == 'setup_intent.succeeded':
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
            payment_method_id=pm_obj["id"],
            card_brand=pm_obj["card"]["brand"],
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
