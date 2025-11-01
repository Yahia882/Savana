from django.urls import path
from . import views

urlpatterns = [
    path("ReviewPublishedProductsView/",views.ReviewPublishedProductsView.as_view()),
    path("ReviewPublishedProductsView/<int:pk>/",views.ReviewPublishedProductsView.as_view()),
]
