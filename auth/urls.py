from django.conf import settings
from django.urls import include, path
from .views import RegisterView, LoginView, SendOrResendSMSAPIView, VerifyPhoneNumberAPIView ,password_reset_confirm_redirect,email_confirm_redirect
from dj_rest_auth.views import LogoutView, PasswordResetConfirmView, PasswordResetView, PasswordChangeView
from dj_rest_auth.registration.views import VerifyEmailView, ResendEmailVerificationView
urlpatterns = [
    path("signup/", RegisterView.as_view(), name="user_register"),
    path("login/", LoginView.as_view(), name="user_login"),
    path(
        "logout/", LogoutView.as_view(), name="verify_phone_number"
    ),
    path('verify-email/', VerifyEmailView.as_view(), name='rest_verify_email'),
    path("account-confirm-email/<str:key>/",
         email_confirm_redirect, name="account_confirm_email"),
    path('resend-email/', ResendEmailVerificationView.as_view(),
         name="rest_resend_email"),
    path('password/reset/', PasswordResetView.as_view(),
         name='rest_password_reset'),
    path(
        "password/reset/confirm/<str:uidb64>/<str:token>",
        password_reset_confirm_redirect,
        name="password_reset_confirm",
    ),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(),
         name='rest_password_reset_confirm'),
    path('password/change/', PasswordChangeView.as_view(),
         name='rest_password_change'),
]

if settings.LOGIN_WITH_PHONE_NUMBER:
    urlpatterns += [
        path("send-sms/", SendOrResendSMSAPIView.as_view(), name="send_resend_sms"),
        path(
            "verify-phone/", VerifyPhoneNumberAPIView.as_view(), name="verify_phone_number"
        ),
    ]
