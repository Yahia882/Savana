from dj_rest_auth.views import LogoutView
from rest_framework import serializers
from requests.exceptions import HTTPError
from dj_rest_auth.registration.serializers import SocialLoginSerializer
from django.http import HttpResponseRedirect,HttpResponse
from django.conf import settings
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import RegisterView, SocialLoginView
from dj_rest_auth.views import LoginView
from django.contrib.auth import get_user_model 
from django.utils.translation import gettext as _
from rest_framework import permissions, status
from dj_rest_auth.app_settings import api_settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from dj_rest_auth.views import PasswordResetView
from rest_framework.generics import (
    GenericAPIView,
    RetrieveAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Address, PhoneNumber, Profile
from .permissions import IsUserAddressOwner, IsUserProfileOwner
from .serializers import (
    PhoneNumberSerializer,
    UserLoginSerializer,
    UserRegistrationSerializer,
    VerifyPhoneNumberSerialzier,
    CustompasswordResetSerializer
)



User = get_user_model()


class UserRegisterationAPIView(RegisterView):
    """
    Register new users using phone number or email and password.
    """
    
    def get_serializer_class(self):
        if settings.LOGIN_WITH_PHONE_NUMBER:
            self.serializer_class = UserRegistrationSerializer
        else:
            self.serializer_class = api_settings.REGISTER_SERIALIZER

    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)


        response_data = ""

        if settings.LOGIN_WITH_PHONE_NUMBER:

            email = request.data.get("email", None)
            phone_number = request.data.get("phone_number", None)

            if email and phone_number:
                res = SendOrResendSMSAPIView.as_view()(request._request, *args, **kwargs)

                if res.status_code == 200:
                    response_data = {"detail": _(
                        "Verification e-mail and SMS sent.")}

            elif email and not phone_number:
                response_data = {"detail": _("Verification e-mail sent.")}

            else:
                res = SendOrResendSMSAPIView.as_view()(request._request, *args, **kwargs)

                if res.status_code == 200:
                    response_data = {"detail": _("Verification SMS sent.")}
        else :
            response_data = {"detail": _("Verification e-mail sent.")}

        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
    


class SendOrResendSMSAPIView(GenericAPIView):
    """
    Check if submitted phone number is a valid phone number and send OTP.
    """

    serializer_class = PhoneNumberSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Send OTP
            phone_number = str(serializer.validated_data["phone_number"])

            user = User.objects.filter(
                phone__phone_number=phone_number).first()

            sms_verification = PhoneNumber.objects.filter(
                user=user, is_verified=False
            ).first()

            sms_verification.send_confirmation()

            return Response(status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyPhoneNumberAPIView(GenericAPIView):
    """
    Check if submitted phone number and OTP matches and verify the user.
    """
    
    serializer_class = VerifyPhoneNumberSerialzier

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            message = {"detail": _("Phone number successfully verified.")}
            return Response(message, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class UserLoginAPIView(LoginView):
    """
    Authenticate existing users using phone number or email and password.
    """
    
    def get_serializer_class(self):
        if settings.LOGIN_WITH_PHONE_NUMBER:
            self.serializer_class = UserLoginSerializer
        else:
            self.serializer_class = api_settings.LOGIN_SERIALIZER



class CustomizedPasswordResetView(PasswordResetView):
    """
    Calls Django Auth PasswordResetForm save method.

    Accepts the following POST parameters: email
    Returns the success/fail message.
    """
    
    def get_serializer_class(self):
        if settings.LOGIN_WITH_PHONE_NUMBER:
            self.serializer_class = CustompasswordResetSerializer
        else:
            self.serializer_class = api_settings.PASSWORD_RESET_SERIALIZER

    def post(self, request, *args, **kwargs):
        # Create a serializer with request.data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()
        # Return the success message with OK HTTP status
        if serializer.validated_data.get("phone"):
            return Response(
                {'detail': _('Password reset code has been sent to your phonenumber.')},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {'detail': _('Password reset e-mail has been sent.')},
                status=status.HTTP_200_OK,
            )


def email_confirm_redirect(request, key):
    return HttpResponseRedirect(
        f"{settings.EMAIL_CONFIRM_REDIRECT_BASE_URL}{key}/"
    )


def password_reset_confirm_redirect(request, uidb64, token):
    return HttpResponseRedirect(
        f"{settings.PASSWORD_RESET_CONFIRM_REDIRECT_BASE_URL}{uidb64}/{token}/"
    )