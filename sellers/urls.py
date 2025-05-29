from django.urls import path
from . import views


urlpatterns = [
    path("account_session/",views.test_Onboarding.as_view()),
    path("onboard/",views.onboarding.as_view()),
    path("seller_payment/",views.sellerPaymentMethod.as_view()),
    path("account_management/",views.test_account_management.as_view()),
    path("notification_banner/",views.test_notification_banner.as_view()),
    path("location/",views.location.as_view()),
    path("signup/",views.signup.as_view()),
]
