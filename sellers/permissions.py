from rest_framework.permissions import BasePermission
from django.core.exceptions import RelatedObjectDoesNotExist
from rest_framework.exceptions import PermissionDenied
class is_seller_verified(BasePermission):
    def has_permission(self, request, view):
        try:
            seller = request.user.seller
        except RelatedObjectDoesNotExist:
            raise PermissionDenied(detail="you don't have a seller account")
        if not seller.is_verifed:
            return False
        return True
