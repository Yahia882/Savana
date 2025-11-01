from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status , exceptions
from sellers.models import ProductIdentity  
from .serializers import AddToCartSerializer, ProductSerializer,ProductDetailSerializer, ViewCartSerializer,CountUpdateSerializer
from rest_framework import permissions
from .models import Cart

class ProductGetListView(generics.GenericAPIView):
   authentication_classes = []
   permission_classes = []


   def get(self, request,**kwargs):
       if kwargs.get("pk"):
            product = ProductIdentity.objects.get(status = "approved", id = kwargs["pk"])
            serializer = ProductDetailSerializer(product)
            return Response(serializer.data)
       else:
            products = ProductIdentity.objects.filter(status = "approved")
            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data)

class AddToCartView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AddToCartSerializer
    
    def post(self, request, format=None):
        serializer  = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    def get(self, request, format=None):
        try:
            instance = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response({"detail": "Cart is empty."},)
        serializer = ViewCartSerializer(instance)
        return Response(serializer.data)
    
    def put(self, request, format=None):
        serializer = CountUpdateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        instance = Cart.objects.get(user=request.user)
        serializer = ViewCartSerializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request):
        cart = Cart.objects.get(user=request.user)
        cart.items = {}
        cart.save()
        return Response({"detail": "Cart cleared."}, status=status.HTTP_200_OK)
    
class CheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    # create checkout model
    # serializer is one model serializer for checkout model
    def get(self,request):
        pass
    # return default address
    # stripe client secret return default payment method and the related stuff 
    # after you calculate the total amount from stripe you store it in the checkout instance 
    # you create the order after payment is confirmed through webhooks 

    def put (self, request):
        # change address or adding discount code 
        pass

    def post(self, request, format=None):
        # in case of the user chooses COD you create the order here
        cart = Cart.objects.get(user=request.user)
        if not cart.items:
            return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)
        
        cart.items = {}
        cart.save()
        return Response({"detail": "Checkout successful and cart cleared."}, status=status.HTTP_200_OK)
    