from dj_rest_auth.jwt_auth import get_refresh_view
from rest_framework_simplejwt.views import TokenVerifyView
from django.conf import settings
from django.urls import  path
from dj_rest_auth.views import LogoutView, PasswordResetConfirmView, PasswordChangeView
from dj_rest_auth.registration.views import VerifyEmailView, ResendEmailVerificationView
from django.views.generic import TemplateView
from .views import (UserRegisterationAPIView, UserLoginAPIView, SendOrResendSMSAPIView, CustomizedPasswordResetView,
                    VerifyResetCodeView, NewPasswordView, VerifyPhoneNumberAPIView, UserAPIView,ManageAddressBook,VerifyAddressPhoneNumber,GoogleLogin , FacebookLogin , AppleLogin, password_reset_confirm_redirect, email_confirm_redirect)

urlpatterns = [
    path("signup/", UserRegisterationAPIView.as_view(), name="user_register"),
    path("login/", UserLoginAPIView.as_view(), name="user_login"),
    path(
        "logout/", LogoutView.as_view(), name="verify_phone_number"
    ),
    path('verify-email/', VerifyEmailView.as_view(), name='rest_verify_email'),
    path("account-confirm-email/<str:key>/",
         email_confirm_redirect, name="account_confirm_email"),
    path('resend-email/', ResendEmailVerificationView.as_view(),
         name="rest_resend_email"),
    path('password/reset/', CustomizedPasswordResetView.as_view(),
         name='rest_password_reset'),
    path(
        "password/reset/confirm/<str:uidb64>/<str:token>",
        password_reset_confirm_redirect,
        name="password_reset_confirm",
    ),
    path('password/reset/confirm/email/', PasswordResetConfirmView.as_view(),
         name='rest_password_reset_confirm'),
    path('password/reset/confirm/phonenumber/', VerifyResetCodeView.as_view(),
         ),
    path('password/reset/newpassword/', NewPasswordView.as_view(),
         name='rest_password_change'),
    path('password/change/', PasswordChangeView.as_view(),
         name='rest_password_change'),
    path(
        'account-email-verification-sent/', TemplateView.as_view(),
        name='account_email_verification_sent',
    ),
    path("", UserAPIView.as_view(), name="user_detail"),
    #path("profile/", ProfileAPIView.as_view(), name="profile_detail"),
    path("address/",ManageAddressBook.as_view()),
    path("address/<int:pk>",ManageAddressBook.as_view()),
    path("verify-address-phone/",VerifyAddressPhoneNumber.as_view()),
    path("google/login/",GoogleLogin.as_view(),name="google_login"),
    path("facebook/login/",FacebookLogin.as_view(),name="FB_login"),
    path("apple/login/",AppleLogin.as_view(),name="Apple_login"),
]

if settings.LOGIN_WITH_PHONE_NUMBER:
    urlpatterns += [
        path("send-sms/", SendOrResendSMSAPIView.as_view(), name="send_resend_sms"),
        path(
            "verify-phone/", VerifyPhoneNumberAPIView.as_view(), name="verify_phone_number"
        ),
    ]


urlpatterns += [
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('token/refresh/', get_refresh_view().as_view(), name='token_refresh'),
]
