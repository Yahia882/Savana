from dj_rest_auth.utils import jwt_encode
from django.http import HttpResponseRedirect
from django.conf import settings
from dj_rest_auth.views import LoginView,sensitive_post_parameters_m,PasswordResetView
from django.contrib.auth import get_user_model 
from django.utils.translation import gettext as _
from rest_framework import permissions, status,mixins
from dj_rest_auth.app_settings import api_settings
from rest_framework.permissions import  IsAuthenticated
from rest_framework.generics import (
    GenericAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.response import Response
from dj_rest_auth.registration.views import RegisterView
from .models import PhoneNumber,Address
from .permissions import ResetPassword,IsUserAddressOwner
from .serializers import (
    PhoneNumberSerializer,
    UserLoginSerializer,
    UserRegistrationSerializer,
    VerifyPhoneNumberSerialzier,
    CustompasswordResetSerializer,
    VerifyResetCodeSerializer,
    NewPasswordViewSerializer,
    UserSerializer,
    AddressSerializer,
    VerifyAddressPhoneSerializer
)
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.apple.views import AppleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.views.decorators.csrf import csrf_exempt

User = get_user_model()

@csrf_exempt  
class UserRegisterationAPIView(RegisterView):
    """
    Register new users using phone number or email and password.
    """
    def get_serializer_class(self):
        if settings.LOGIN_WITH_PHONE_NUMBER:
            return UserRegistrationSerializer
        else:
            return api_settings.REGISTER_SERIALIZER

    
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
                else:
                    return res
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

            sms_verification.send_confirmation(confirmation_method = request.data.get("confirmation_method"))

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

class VerifyResetCodeView(GenericAPIView):
    serializer_class = VerifyResetCodeSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data.get("user")
            access , refresh = jwt_encode(user)
            data = {"access":str(access),"refresh":str(refresh)}
            return Response(data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class NewPasswordView(GenericAPIView):
    serializer_class = NewPasswordViewSerializer
    permission_classes = [IsAuthenticated,ResetPassword]

    @sensitive_post_parameters_m
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': _('New password has been saved.')})

@csrf_exempt  
class UserLoginAPIView(LoginView):
    """
    Authenticate existing users using phone number or email and password.
    """
    
    def get_serializer_class(self):
        if settings.LOGIN_WITH_PHONE_NUMBER:
            return  UserLoginSerializer
        else:
            return api_settings.LOGIN_SERIALIZER



class CustomizedPasswordResetView(PasswordResetView):
    """
    Calls Django Auth PasswordResetForm save method.

    Accepts the following POST parameters: email
    Returns the success/fail message.
    """
    
    def get_serializer_class(self):
        if settings.LOGIN_WITH_PHONE_NUMBER:
            return CustompasswordResetSerializer
        else:
            return api_settings.PASSWORD_RESET_SERIALIZER

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

@csrf_exempt  
class UserAPIView(RetrieveUpdateAPIView):
    """
    Get user details
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        data = serializer.data
        if serializer.validated_data.get("email"):
            data.update({"email_detail": _("Verification e-mail sent.")})
        if serializer.validated_data.get("phone_number"):
            p=PhoneNumber.objects.get(user = request.user)
            p.send_confirmation(confirmation_method = request.data.get("confirmation_method"))
            data.update({"phone_detail": _("Verification SMS sent.")})
        data.update({"updated_successfully":serializer.validated_data})
        data["updated_successfully"].pop("email",None)
        data["updated_successfully"].pop("phone_number",None)
        return Response(data)
    
class AddressMixin(GenericAPIView,mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, mixins.UpdateModelMixin):
    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        if pk is not None:
            return self.retrieve(request, *args, **kwargs)
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
    
class ManageAddressBook(AddressMixin):
    permission_classes = [IsUserAddressOwner]
    serializer_class = AddressSerializer

    def get_queryset(self):
        return Address.objects.filter(user = self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        phone =serializer.validated_data.get("phone_detail")
        headers = self.get_success_headers(serializer.data)
        data = serializer.data
        if phone:
            data.update({"phone_detail":phone})
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        phone =serializer.validated_data.get("phone_detail")
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        data = serializer.data
        if phone:
            data.update({"phone_detail":phone})
        return Response(data)
    

class VerifyAddressPhoneNumber(GenericAPIView):
    """
    Check if submitted phone number and OTP matches and verify the user.
    """
    
    serializer_class = VerifyAddressPhoneSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            message = {"detail": _("Phone number successfully verified.")}
            return Response(message, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://localhost:8111/user/login/google"
    client_class = OAuth2Client

class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter
    
class AppleLogin(SocialLoginView):
    adapter_class = AppleOAuth2Adapter
