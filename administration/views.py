from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from sellers.models import ProductIdentity
from .serializers import ReviewPublishedProductsSerializer,ProductSerializer, ProductDetailSerializer
from sellers.generics import ListRetrieveUpdate
from .permissions import CanReview

class ReviewPublishedProductsView(ListRetrieveUpdate):
    permission_classes = [CanReview]
    queryset = ProductIdentity.objects.filter(status = "pending")

    def get_serializer_class(self):

        if self.request.method == "GET" and self.kwargs.get("pk"):
            return ProductDetailSerializer
        
        if self.request.method == "GET":
            return ProductSerializer
        
        if self.request.method == "PUT":
            return ReviewPublishedProductsSerializer

        return super().get_serializer_class()
    
