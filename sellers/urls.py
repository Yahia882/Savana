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
    path("store_info/",views.StoreInfo.as_view()),
    path("connected_acc_webhook/",views.connected_acc_webhook_view),
    path("platform_acc_webhook/",views.account_webhook_view),
    path("verify_seller/",views.VerifySeller.as_view()),
    path("verify_seller/<int:pk>",views.VerifySeller.as_view()),
    path("set_product_identity/",views.ProductIdentityView.as_view()),
    path("set_variation_parameters/",views.VariationParameters.as_view()),
    path("set_variation_offer/",views.VariationsOffer.as_view()),
    path("set_one_product_offer/",views.OneProductOffer.as_view()),
    path("set_product_description/",views.ProductDescription.as_view()),
    path("set_product_details/",views.ProductDetails.as_view()),
    path("save_as_draft/",views.SaveDraft.as_view()),
    path("save_as_draft/<str:pk>/",views.SaveDraft.as_view()),
    path("publish_product/",views.PublishProduct.as_view()),
]
