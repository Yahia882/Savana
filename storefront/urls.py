from django.urls import path
from . import views

urlpatterns = [
    path("listproducts/",views.ProductGetListView.as_view()),
    path("listproducts/<int:pk>/",views.ProductGetListView.as_view()),
    path("add_to_cart/",views.AddToCartView.as_view()),
]
