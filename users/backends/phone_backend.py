import phonenumbers
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from phonenumbers.phonenumberutil import NumberParseException

User = get_user_model()


class PhoneNumberAuthBackend(ModelBackend):
    
    """
    Custom authentication backend to login users using phone number.
    """

    def authenticate(self, request, username=None, password=None):
            if not username:
                return
            try:
                user = User.objects.get(phone__phone_number=username)
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                return
        
