import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField
from rest_framework.exceptions import NotAcceptable
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

User = get_user_model()
twilio_account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
twilio_auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
twilio_phone_number = getattr(settings, "TWILIO_PHONE_NUMBER", None)
twilio_client = Client(twilio_account_sid, twilio_auth_token)


def generate_security_code():
    """
    Returns a unique random `security_code` for given `TOKEN_LENGTH` in the settings.
    Default token length = 6
    """
    token_length = getattr(settings, "TOKEN_LENGTH", 6)
    return get_random_string(token_length, allowed_chars="0123456789")


class PassowrdReset(models.Model):
    user = models.OneToOneField(
        User, related_name="passwordreset", on_delete=models.CASCADE)
    code = models.CharField(max_length=120, null=True)
    sent = models.DateTimeField(null=True)
    password_expiration = models.DateTimeField(null=True)

    def is_security_code_expired(self):
        expiration_date = self.sent + datetime.timedelta(
            minutes=settings.TOKEN_EXPIRE_MINUTES
        )
        return expiration_date <= timezone.now()

    def send_passwordreset_code(self, confirmation_method=None):

        self.code = generate_security_code()

        if all([twilio_account_sid, twilio_auth_token, twilio_phone_number]):
            try:
                if confirmation_method == "whatsapp":
                    twilio_client.messages.create(
                        from_='whatsapp:+14155238886',
                        content_sid='HX229f5a04fd0510ce1b071852155d3e75',
                        content_variables=f'{{"1": "{self.code}"}}',
                        to=f'whatsapp:{str(self.user.phone.phone_number)}'
                    )
                else:

                    twilio_client.messages.create(
                        body=f"Your password reset code is {self.code}",
                        to=str(self.user.phone.phone_number),
                        from_=twilio_phone_number,
                    )
                self.sent = timezone.now()
                self.save()
                return True
            except TwilioRestException as e:
                print(e)
        else:
            print("Twilio credentials are not set")

    def check_passwordreset_code(self, security_code):
        if (
            not self.is_security_code_expired()
            and security_code == self.code
        ):
            self.password_expiration = timezone.now() + datetime.timedelta(minutes=5)
            self.save()
            return True
        else:
            raise NotAcceptable(
                _(
                    "Your security code is wrong or expired."
                )
            )


class PhoneNumber(models.Model):
    user = models.OneToOneField(
        User, related_name="phone", on_delete=models.CASCADE)
    phone_number = PhoneNumberField(unique=True)
    security_code = models.CharField(max_length=120, null=True)
    is_verified = models.BooleanField(default=False)
    sent = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    temp_phone = PhoneNumberField(null=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.phone_number.as_e164

    def is_security_code_expired(self):
        expiration_date = self.sent + datetime.timedelta(
            minutes=settings.TOKEN_EXPIRE_MINUTES
        )
        return expiration_date <= timezone.now()

    def send_confirmation(self, confirmation_method=None):
        self.security_code = generate_security_code()

        if all([twilio_account_sid, twilio_auth_token, twilio_phone_number]):
            try:
                phone = self.temp_phone if self.temp_phone else self.phone_number
                if confirmation_method == "whatsapp":
                    twilio_client.messages.create(
                        from_='whatsapp:+14155238886',
                        content_sid='HX229f5a04fd0510ce1b071852155d3e75',
                        content_variables=f'{{"1": "{self.security_code}"}}',
                        to=f'whatsapp:{str(phone)}'
                    )

                else:
                    twilio_client.messages.create(
                        body=f"Your activation code is {self.security_code}",
                        to=str(phone),
                        from_=twilio_phone_number,
                    )

                self.sent = timezone.now()
                self.save()
                return True
            except TwilioRestException as e:
                print(e)
        else:
            print("Twilio credentials are not set")

    def check_verification(self, security_code):
        if (
            not self.is_security_code_expired()
            and security_code == self.security_code
        ):
            if self.temp_phone:
                self.phone_number = self.temp_phone
                self.temp_phone = None
            self.is_verified = True
            self.save()
        else:
            raise NotAcceptable(
                _(
                    "Your security code is wrong, expired or this phone is verified before."
                )
            )

        return self.is_verified


class Profile(models.Model):
    user = models.OneToOneField(
        User, related_name="profile", on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to="avatar", blank=True)
    bio = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.user.get_full_name()


class AddressPhoneNumber(models.Model):
    user = models.ForeignKey(User,related_name="addressphonenumber",on_delete=models.CASCADE)
    phone_number = PhoneNumberField()
    security_code = models.CharField(max_length=120, null=True)
    is_verified = models.BooleanField(default=False)
    sent = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "phone_number")]
    def is_security_code_expired(self):
        expiration_date = self.sent + datetime.timedelta(
            minutes=settings.TOKEN_EXPIRE_MINUTES
        )
        return expiration_date <= timezone.now()

    def send_confirmation(self, confirmation_method=None):

        self.security_code = generate_security_code()

        if all([twilio_account_sid, twilio_auth_token, twilio_phone_number]):
            try:
                if confirmation_method == "whatsapp":
                    message =twilio_client.messages.create(
                        from_='whatsapp:+14155238886',
                        content_sid='HX229f5a04fd0510ce1b071852155d3e75',
                        content_variables=f'{{"1": "{self.security_code}"}}',
                        to=f'whatsapp:{str(self.phone_number)}'
                    )
                    print(message)
                else:
                    twilio_client.messages.create(
                        body=f"Your activation code is {self.security_code}",
                        to=str(self.phone_number),
                        from_=twilio_phone_number,
                    )
                self.sent = timezone.now()
                self.save()
                return True
            except TwilioRestException as e:
                print(e)
        else:
            print("Twilio credentials are not set")

    def check_verification(self, security_code):
        if (
            not self.is_security_code_expired()
            and security_code == self.security_code
            and not self.is_verified
        ):
            self.is_verified = True
            self.save()
        else:
            raise NotAcceptable(
                _(
                    "Your security code is wrong, expired or this phone is verified before."
                )
            )

        return self.is_verified

    def __str__(self):
        return str(self.phone_number)
class Address(models.Model):

    user = models.ForeignKey(
        User, related_name="addresses", on_delete=models.CASCADE)
    default = models.BooleanField(default=False)
    country = CountryField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length = 100)
    street_address = models.CharField(max_length=100)
    building_address = models.CharField(max_length=100,default="hqouqeen 1")
    apartment_address = models.CharField(max_length=100,blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    phone_number = models.ForeignKey(
        AddressPhoneNumber,  on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.user.get_full_name()

class Customer(models.Model):
    user = models.OneToOneField(
        User, related_name="customer", on_delete=models.CASCADE)
    customer_id = models.CharField(max_length=100,unique=True)

class PaymentMethod(models.Model):
    customer = models.ForeignKey(Customer,related_name="paymentmethods",on_delete=models.CASCADE)
    Payment_method_id = models.CharField(max_length=100,unique=True)
    default = models.BooleanField(default=False)
    card_brand = models.CharField(max_length=100)
    last4 = models.IntegerField()
    exp_month = models.IntegerField()
    exp_year = models.IntegerField()
    funding = models.CharField(max_length=20, blank=True, null=True)