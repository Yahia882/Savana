from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import PasswordResetSerializer
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import gettext as _
from django_countries.serializers import CountryFieldMixin
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from allauth.account.adapter import get_adapter
from django.core.exceptions import ValidationError as DjangoValidationError
from allauth.account.utils import setup_user_email
from .serializerfields import phonefield
from .exceptions import (
    AccountDisabledException,
    AccountNotRegisteredException,
    InvalidCredentialsException,
)
from .models import Address, PhoneNumber, Profile
from .validators import validate_email_or_phonenumber
import re
User = get_user_model()



class UserRegistrationSerializer(RegisterSerializer):
    """
    Serializer for registrating new users using email or phone number.
    """

    username = None
    first_name = serializers.CharField(required=True, write_only=True)
    last_name = serializers.CharField(required=True, write_only=True)
    phone_number = phonefield(
        required=False,
        write_only=True,
        validators=[
            UniqueValidator(
                queryset=PhoneNumber.objects.all(),
                message=_("A user is already registered with this phone number."),
            )
        ],
    )
    email = serializers.EmailField(required=False)

    def validate(self, validated_data):
        email = validated_data.get("email", None)
        phone_number = validated_data.get("phone_number", None)

        if not (email or phone_number):
            raise serializers.ValidationError(_("Enter an email or a phone number."))

        if validated_data["password1"] != validated_data["password2"]:
            raise serializers.ValidationError(
                _("The two password fields didn't match.")
            )

        return validated_data

    def get_cleaned_data_extra(self):
        return {
            "phone_number": self.validated_data.get("phone_number", ""),
            "first_name": self.validated_data.get("first_name", ""),
            "last_name": self.validated_data.get("last_name", ""),
        }

    def create_extra(self, user, validated_data):
        user.first_name = self.validated_data.get("first_name")
        user.last_name = self.validated_data.get("last_name")
        user.save()

    def custom_signup(self, request, user):
        self.create_extra(user, self.get_cleaned_data_extra())
    
    def get_cleaned_data(self):
        return {
            'username': self.validated_data.get('username', ''),
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'phone_number': self.validated_data.get("phone_number",''),
        }
    def populate_username(self, request, user,phone):
        """
        Fills in a valid username, if required and missing.  If the
        username is already present it is assumed to be valid
        (unique).
        """
        from allauth.account.utils import user_email, user_field, user_username
        from allauth.account import app_settings

        first_name = user_field(user, "first_name")
        last_name = user_field(user, "last_name")
        email = user_email(user)
        username = user_username(user)
        if app_settings.USER_MODEL_USERNAME_FIELD:
            user_username(
                user,
                username
                or self.generate_unique_username(
                    [first_name, last_name, email, username,phone, "user"]
                ),
            )
    
    def save_user(self, request, user, form, commit=True):
        """
        Saves a new `User` instance using information provided in the
        signup form.
        """
        from allauth.account.utils import user_email, user_field, user_username

        data = form.cleaned_data
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        username = data.get("username")
        phone_number = data.get("phone_number")
        if PhoneNumber.objects.filter(phone_number=phone_number).exists():
            phone_number = None
        user_email(user, email)
        user_username(user, username)
        if first_name:
            user_field(user, "first_name", first_name)
        if last_name:
            user_field(user, "last_name", last_name)
        if "password1" in data:
            user.set_password(data["password1"])
        else:
            user.set_unusable_password()
        self.populate_username(request, user,phone_number)
        if commit:
            # Ability not to commit makes it easier to derive from
            # this adapter by adding
            user.save()
            if phone_number:
                p = PhoneNumber(user = user,phone_number=phone_number)
                p.save()
           
        return user
    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        user = self.save_user(request, user, self, commit=False)
        if "password1" in self.cleaned_data:
            try:
                adapter.clean_password(self.cleaned_data['password1'], user=user)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(
                    detail=serializers.as_serializer_error(exc)
            )
        user.save()
        self.custom_signup(request, user)
        setup_user_email(request, user, [])
        return user
       
       
class UserLoginSerializer(serializers.Serializer):
    """
    Serializer to login users with email or phone number.
    """

    username = serializers.CharField(validators = [validate_email_or_phonenumber],required=True)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    

    def validate(self, validated_data):
        username = validated_data.get("username")
        password = validated_data.get("password")
        value = email_or_phone(username)
        email = value.get("email")
        phone = value.get("phone")
        user = None
        user = authenticate(username = username,password=password)

        if not user:
            raise InvalidCredentialsException()

        if not user.is_active:
            raise AccountDisabledException()

        if email:
            email_address = user.emailaddress_set.filter(
                email=user.email, verified=True
            ).exists()
            if not email_address:
                raise serializers.ValidationError(_("E-mail is not verified."))

        else:
            if not user.phone.is_verified:
                raise serializers.ValidationError(_("Phone number is not verified."))

        validated_data["user"] = user
        return validated_data
    
    
class PhoneNumberSerializer(serializers.ModelSerializer):
    """
    Serializer class to serialize phone number.
    """

    phone_number = phonefield()

    class Meta:
        model = PhoneNumber
        fields = ("phone_number",)

    def validate_phone_number(self, value):
        try:
            queryset = User.objects.get(phone__phone_number=value)
            if queryset.phone.is_verified:
                err_message = _("Phone number is already verified")
                raise serializers.ValidationError(err_message)

        except User.DoesNotExist:
            raise AccountNotRegisteredException()

        return value
    
    
class VerifyPhoneNumberSerialzier(serializers.Serializer):
    """
    Serializer class to verify OTP.
    """

    phone_number = phonefield()
    otp = serializers.CharField(max_length=settings.TOKEN_LENGTH)

    def validate_phone_number(self, value):
        queryset = User.objects.filter(phone__phone_number=value)
        if not queryset.exists():
            raise serializers.ValidationError("phonenumber is not registered")
        return value

    def validate(self, validated_data):
        phone_number = str(validated_data.get("phone_number"))
        otp = validated_data.get("otp")

        queryset = PhoneNumber.objects.get(phone_number=phone_number)

        queryset.check_verification(security_code=otp)

        return validated_data
    

class CustompasswordResetSerializer(PasswordResetSerializer):
    email = serializers.CharField(validators = [validate_email_or_phonenumber],required=True) 

    def validate_email(self, validated_data):
        email_or_phonenumber = validated_data.get("email")
        value = email_or_phone(email_or_phonenumber)
        email = value.get("email")
        phone = value.get("phone")
        if email:    
        # Create PasswordResetForm with the serializer
            self.reset_form = self.password_reset_form_class(data=self.initial_data)
            if not self.reset_form.is_valid():
                raise serializers.ValidationError(self.reset_form.errors)
            self.validated_data["user_email"]= email
            return validated_data
        else:
            queryset = User.objects.filter(phone__phone_number=phone)
            if not queryset.exists():
                raise serializers.ValidationError("phonenumber is not registered")
            if not queryset.phone.is_verified:
                raise serializers.ValidationError("phonenumber is not verified")
            self.validated_data["phone"]= phone
 
    def save(self):
        if self.validated_data.get("user_email"):
            if 'allauth' in settings.INSTALLED_APPS:
                from allauth.account.forms import default_token_generator
            else:
                from django.contrib.auth.tokens import default_token_generator

            request = self.context.get('request')
            # Set some values to trigger the send_email method.
            opts = {
                'use_https': request.is_secure(),
                'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL'),
                'request': request,
                'token_generator': default_token_generator,
            }

            opts.update(self.get_email_options())
            self.reset_form.save(**opts)
        else:
            phone = self.validated_data.get("phone")
            sms_verification = PhoneNumber.objects.filter(
                phone_number=phone, is_verified=True
            ).first()

            sms_verification.send_passwordreset_code()
            




def email_or_phone(self,value):
    phone_regex = r"^\+?[1-9]\d{1,14}$"
    if re.match(phone_regex,value):
        return {"phone":value}
    else:
        return {"email":value}