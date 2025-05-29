from rest_framework_simplejwt.tokens import Token
from rest_framework_simplejwt.settings import api_settings
from dj_rest_auth.app_settings import api_settings as dj_rest_auth_api_settings
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from dj_rest_auth.jwt_auth import JWTCookieAuthentication
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.tokens import AccessToken

class CustomizedToken(AccessToken):
    def verify(self) -> None:
        
        #if "role" not in self.payload or self.payload["role"] != "seller":
        if self.payload.get("role","customer") != "seller":
            raise TokenError(_("Token is not valid for this user type"))

        self.check_exp()

        if (
            api_settings.JTI_CLAIM is not None
            and api_settings.JTI_CLAIM not in self.payload
        ):
            raise TokenError(_("Token has no id"))

        if api_settings.TOKEN_TYPE_CLAIM is not None:
            self.verify_token_type()


class SellerJWTCookieAuthentication(JWTCookieAuthentication):
    def authenticate(self, request):
        cookie_name = dj_rest_auth_api_settings.JWT_AUTH_COOKIE
        header = self.get_header(request)
        if header is None:
            if cookie_name:
                raw_token = request.COOKIES.get(cookie_name)
                if dj_rest_auth_api_settings.JWT_AUTH_COOKIE_ENFORCE_CSRF_ON_UNAUTHENTICATED:  # True at your own risk
                    self.enforce_csrf(request)
                elif raw_token is not None and dj_rest_auth_api_settings.JWT_AUTH_COOKIE_USE_CSRF:
                    self.enforce_csrf(request)
            else:
                return None
        else:
            raw_token = self.get_raw_token(header)

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token

    def get_validated_token(self, raw_token: bytes) -> Token:
        """
        Validates an encoded JSON web token and returns a validated token
        wrapper object.
        """
        messages = []

        try:
            return CustomizedToken(raw_token)
        except TokenError as e:
            messages.append(
                {
                    "token_class": CustomizedToken.__name__,
                    "token_type": CustomizedToken.token_type,
                    "message": e.args[0],
                }
            )

        raise InvalidToken(
            {
                "detail": _("Given token not valid for any token type"),
                "messages": messages,
            }
        )
