from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
import stripe
from rest_framework import permissions
from django.core.exceptions import ObjectDoesNotExist
from decouple import config
from django.conf import settings
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
    def post(self,request):
        account_session=stripe.AccountSession.create(
            account='acct_1QLnJNPxFPhF2bZ9',
            components={
                "notification_banner": {
                    "enabled": True,
                    "features": {"external_account_collection": True},
                },
            },
        )
        return Response({'client_secret': account_session.client_secret,})


class signup(APIView):
    permission_classes = [permissions.IsAuthenticated,]
    def post(request,*args, **kwargs):
        try:
            status = request.user.seller.status
        except ObjectDoesNotExist:
            return Response({"status":"location"})
        for key,value in status.items():
            if value == False:
                return Response({"status":key})
        return Response({"status":"verified"})
    



class login(APIView):
    pass

class test_web_hook(APIView):
    pass