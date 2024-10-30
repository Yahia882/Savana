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
from .fields import phonefield
from django.db.models import Q
from allauth.account import signals
from .exceptions import (
    AccountDisabledException,
    AccountNotRegisteredException,
    InvalidCredentialsException,
)
from .models import Address, PhoneNumber, Profile, PassowrdReset,AddressPhoneNumber
from .validators import validate_email_or_phonenumber, validate_phone_number
import re
from django.contrib.auth.forms import SetPasswordForm
from allauth.account.utils import user_email, user_field, user_username
from allauth.account.forms import AddEmailForm
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
                message=_(
                    "A user is already registered with this phone number."),
            )
        ],
    )
    email = serializers.EmailField(required=False)

    def validate(self, validated_data):
        email = validated_data.get("email", None)
        phone_number = validated_data.get("phone_number", None)

        if not (email or phone_number):
            raise serializers.ValidationError(
                _("Enter an email or a phone number."))

        if validated_data["password1"] != validated_data["password2"]:
            raise serializers.ValidationError(
                _("The two password fields didn't match.")
            )

        return validated_data

    # def get_cleaned_data_extra(self):
    #     return {
    #         "phone_number": self.validated_data.get("phone_number", ""),
    #         "first_name": self.validated_data.get("first_name", ""),
    #         "last_name": self.validated_data.get("last_name", ""),
    #     }

    def create_extra(self, user, validated_data):
        user.first_name = self.validated_data.get("first_name")
        user.last_name = self.validated_data.get("last_name")
        user.save()

    def get_cleaned_data(self):
        return {
            "first_name": self.validated_data.get("first_name", ""),
            "last_name": self.validated_data.get("last_name", ""),
            'username': self.validated_data.get('username', ''),
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'phone_number': self.validated_data.get("phone_number", ''),
        }

    def populate_username(self, request, user, phone):
        """
        Fills in a valid username, if required and missing.  If the
        username is already present it is assumed to be valid
        (unique).
        """
        from allauth.account.utils import user_email, user_field, user_username
        from allauth.account import app_settings
        adapter = get_adapter()
        first_name = user_field(user, "first_name")
        last_name = user_field(user, "last_name")
        email = user_email(user)
        username = user_username(user)
        if app_settings.USER_MODEL_USERNAME_FIELD:
            user_username(
                user,
                username
                or adapter.generate_unique_username(
                    [first_name, last_name, email, username, phone, "user"]
                ),
            )

    def save_user(self, request, user, form, commit=True):
        """
        Saves a new `User` instance using information provided in the
        signup form.
        """

        adapter = get_adapter()
        data = form.cleaned_data
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        username = data.get("username")
        phone_number = data.get("phone_number")
        if PhoneNumber.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError("phone number already exists")
        user_email(user, email)
        user_username(user, username)
        if first_name:
            user_field(user, "first_name", first_name)
        if last_name:
            user_field(user, "last_name", last_name)
        if "password1" in data:
            user.set_password(data["password1"])
            try:
                adapter.clean_password(
                    self.cleaned_data['password1'], user=user)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(
                    detail=serializers.as_serializer_error(exc)
                )
        else:
            user.set_unusable_password()
        self.populate_username(request, user, phone_number)
        if commit:
            # Ability not to commit makes it easier to derive from
            # this adapter by adding
            user.save()
            if phone_number:
                p = PhoneNumber(user=user, phone_number=phone_number)
                p.save()

        return user

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        user = self.save_user(request, user, self, commit=True)
        self.custom_signup(request, user)
        setup_user_email(request, user, [])
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer to login users with email or phone number.
    """

    username = serializers.CharField(
        validators=[validate_email_or_phonenumber], required=True)
    password = serializers.CharField(
        write_only=True, style={"input_type": "password"})

    def validate(self, validated_data):
        username = validated_data.get("username")
        password = validated_data.get("password")
        value = email_or_phone(username)
        email = value.get("email")
        phone = value.get("phone")
        user = None
        user = authenticate(username=username, password=password)

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
                raise serializers.ValidationError(
                    _("Phone number is not verified."))

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

        is_verified = User.objects.filter(
            phone__phone_number=value, phone__is_verified=True)
        if is_verified:
            raise serializers.ValidationError(
                "this phone number is already verified")
        queryset1 = User.objects.filter(phone__phone_number=value)
        queryset2 = User.objects.filter(phone__temp_phone=value)
        if not queryset1.exists() and not queryset2.exists():
            raise serializers.ValidationError("phonenumber is not registered")
        return value

    def validate(self, validated_data):
        phone_number = str(validated_data.get("phone_number"))
        otp = validated_data.get("otp")
        try:
            queryset = PhoneNumber.objects.get(phone_number=phone_number)
        except:
            queryset = PhoneNumber.objects.get(temp_phone=phone_number)

        queryset.check_verification(security_code=otp)

        return validated_data


class CustompasswordResetSerializer(PasswordResetSerializer):
    email = serializers.CharField(
        validators=[validate_email_or_phonenumber], required=True)

    def validate_email(self, validated_data):
        email_or_phonenumber = self.initial_data.get("email")
        value = email_or_phone(email_or_phonenumber)
        email = value.get("email")
        phone = value.get("phone")
        self.email_or_phone = {}
        if email:
            # Create PasswordResetForm with the serializer
            self.reset_form = self.password_reset_form_class(
                data=self.initial_data)
            if not self.reset_form.is_valid():
                raise serializers.ValidationError(self.reset_form.errors)
            self.email_or_phone["email"] = email
            return validated_data
        else:
            queryset = User.objects.get(phone__phone_number=phone)
            if not queryset:
                raise serializers.ValidationError(
                    "phonenumber is not registered")
            if not queryset.phone.is_verified:
                raise serializers.ValidationError(
                    "phonenumber is not verified")
            self.email_or_phone["phone"] = phone

    def save(self):
        request = self.context.get('request')
        if self.email_or_phone.get("user_email"):
            if 'allauth' in settings.INSTALLED_APPS:
                from allauth.account.forms import default_token_generator
            else:
                from django.contrib.auth.tokens import default_token_generator

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
            phone = self.email_or_phone.get("phone")
            user = User.objects.get(phone__phone_number=phone)
            queryset = None
            try:
                queryset = PassowrdReset.objects.get(user=user)
            except:
                queryset = PassowrdReset.objects.create(user=user)
            self.validated_data["phone"] = phone
            queryset.send_passwordreset_code(
                confirmation_method=request.data.get("confirmation_method"))


class VerifyResetCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        validators=[validate_phone_number], required=True)
    otp = serializers.CharField(max_length=settings.TOKEN_LENGTH)

    def validate_phone_number(self, value):
        queryset = User.objects.get(phone__phone_number=value)
        if not queryset:
            raise serializers.ValidationError("phonenumber is not registered")
        self.user = queryset
        return value

    def validate(self, validated_data):
        otp = validated_data.get("otp")
        try:
            queryset = PassowrdReset.objects.get(user=self.user)
        except:
            raise serializers.ValidationError(
                "that number did not issue a reset password request")
        queryset.check_passwordreset_code(security_code=otp)
        validated_data["user"] = self.user
        return validated_data

class VerifyAddressPhoneSerializer(serializers.Serializer):
    phone_number = phonefield()
    otp = serializers.CharField(max_length=settings.TOKEN_LENGTH)


    def validate(self, validated_data):
        phone_number = str(validated_data.get("phone_number"))
        otp = validated_data.get("otp")
        request = self.context.get("request")
        user = request.user
        q = AddressPhoneNumber.objects.filter(
            phone_number=phone_number, user=user)
        if not q.exists():
            raise serializers.ValidationError("phonenumber does not exist")
        instance = q.first()
        if instance.is_verified:
            raise serializers.ValidationError(
                "this phone number is already verified")
        instance.check_verification(security_code=otp)
        return validated_data
    
class NewPasswordViewSerializer(serializers.Serializer):
    new_password1 = serializers.CharField(max_length=128)
    new_password2 = serializers.CharField(max_length=128)
    set_password_form_class = SetPasswordForm

    set_password_form = None

    def validate(self, attrs):
        request = self.context.get('request')
        self.set_password_form = self.set_password_form_class(
            user=request.user, data=attrs,
        )

        if not self.set_password_form.is_valid():
            raise serializers.ValidationError(self.set_password_form.errors)
        return attrs

    def save(self):
        self.set_password_form.save()


def email_or_phone(value):
    phone_regex = r"^\+?[1-9]\d{1,14}$"
    if re.match(phone_regex, value):
        return {"phone": value}
    else:
        return {"email": value}


class AddressReadOnlySerializer(CountryFieldMixin, serializers.ModelSerializer):
    """
    Serializer class to seralize Address model
    """

    user = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = Address
        fields = "__all__"


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer class to serialize the user Profile model
    """
    joined_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Profile
        fields = (
            "avatar",
            "bio",
            "joined_at",
        )


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer class to seralize User model
    """

    profile = ProfileSerializer(read_only=True)
    bio = serializers.CharField(
        max_length=200, required=False, write_only=True)
    avatar = serializers.ImageField(required=False, write_only=True)
    phone = PhoneNumberField(read_only=True)
    phone_number = phonefield(required=False, write_only=True)
    username = serializers.CharField(required=False)
    change_email_form = None

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "phone_number",
            "first_name",
            "last_name",
            "bio",
            "avatar",
            "profile",
            "phone"
        )

    @property
    def email_change_form(self):
        return AddEmailForm

    def validate_phone_number(self, phone_number):
        request = self.context.get("request")
        query = PhoneNumber.objects.filter(
            phone_number=phone_number, user=request.user)
        if query.exists():
            raise serializers.ValidationError(
                "this phone number is already associated with this account")
        return phone_number

    def validate_username(self, username):
        username = get_adapter().clean_username(username)
        return username

    def validate_email(self, email):
        return RegisterSerializer.validate_email(self, email=email)

    def update(self, instance, validated_data):
        request = self.context.get("request")
        username = validated_data.get("username")
        first_name = validated_data.get("first_name")
        last_name = validated_data.get("last_name")
        email = validated_data.get("email")
        profile_data = {}
        bio = validated_data.get("bio")
        avatar = validated_data.get("avatar")
        phone_number = validated_data.get("phone_number")
        if bio:
            profile_data = {"bio": bio}
        if avatar:
            profile_data.update({"avatar": avatar})
        if first_name:
            user_field(instance, "first_name", first_name)
        if last_name:
            user_field(instance, "last_name", last_name)
        if username:
            user_username(instance, username)
        if profile_data:
            profile = Profile.objects.filter(user=instance.id)
            profile.update(**profile_data)
            profile_instance = profile.first()
            profile_instance.save()
        if email:
            self.change_email_form = self.email_change_form(
                data={"email": email}, user=request.user)
            if not self.change_email_form.is_valid():
                raise serializers.ValidationError(
                    self.change_email_form.errors)
            self.change_email_form.save(request)
        if phone_number:
            try:
                p = PhoneNumber.objects.get(user=request.user)
                p.temp_phone = phone_number
                p.save()
            except:
                PhoneNumber.objects.create(
                    user=request.user, phone_number=phone_number)

        instance.save()
        return instance


class AddressSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only = True)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    phone_number = serializers.CharField(source ="phone_number.phone_number",read_only = True) 
    phone = phonefield(write_only = True)
    class Meta:
        model = Address
        fields = ("id",
                  "user",
                  "country",
                  "city",
                  "postal_code",
                  "street_address",
                  "apartment_address",
                  "phone_number",
                  "phone"
                  )
    def create(self, validated_data):
        user = validated_data.get("user")
        request = self.context.get("request")
        phone = validated_data.pop("phone",None)
        confirmation_method  = request.data.get("confirmation_method")
        instance = Address(**validated_data)
        try:
            addressphone =AddressPhoneNumber.objects.get(user = user,phone_number = phone)
            instance.phone_number = addressphone
            if not addressphone.is_verified:
                addressphone.send_confirmation(confirmation_method=confirmation_method)
                self.validated_data["phone_detail"] = "Verification SMS sent"
        except AddressPhoneNumber.DoesNotExist:
            addressphone =AddressPhoneNumber.objects.create(user = user,phone_number = phone)
            instance.phone_number = addressphone
            addressphone.send_confirmation(confirmation_method=confirmation_method)
            self.validated_data["phone_detail"] = "Verification SMS sent"
        instance.save()
        return instance
    
    def update(self, instance, validated_data):
        phone = validated_data.pop("phone",None)
        instance = super().update(instance, validated_data)
        request = self.context.get("request")
        confirmation_method  = request.data.get("confirmation_method")
        user = request.user
        if phone:
            try:
                addressphone =AddressPhoneNumber.objects.get(user = user,phone_number = phone)
                instance.phone_number = addressphone
                if not addressphone.is_verified:
                    addressphone.send_confirmation(confirmation_method=confirmation_method)
                    self.validated_data["phone_detail"] = "Verification SMS sent"
            except AddressPhoneNumber.DoesNotExist:
                addressphone =AddressPhoneNumber.objects.create(user = user,phone_number = phone)
                instance.phone_number = addressphone
                addressphone.send_confirmation(confirmation_method=confirmation_method)
                self.validated_data["phone_detail"] = "Verification SMS sent"
        instance.save()
        return instance

    