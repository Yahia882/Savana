from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
class CustomizedAllAuthAdapter(DefaultAccountAdapter):

    def get_email_confirmation_url(self, request, emailconfirmation):

        base_url = settings.EMAIL_CONFIRM_REDIRECT_BASE_URL
        key = emailconfirmation.key
        ret = f"{base_url}{key}/"
        return ret