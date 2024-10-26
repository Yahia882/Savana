from django.urls import include, path
from .views import GoogleLogin , FacebookLogin , AppleLogin

urlpatterns = [
    path("google/login/",GoogleLogin.as_view(),name="google_login"),
    path("facebook/login/",FacebookLogin.as_view(),name="FB_login"),
    path("apple/login/",AppleLogin.as_view(),name="Apple_login"),
]
