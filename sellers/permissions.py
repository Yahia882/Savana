from rest_framework.permissions import BasePermission
from django.core.exceptions import ObjectDoesNotExist 
from rest_framework.exceptions import PermissionDenied
class is_seller_verified(BasePermission):
    def has_permission(self, request, view):
        try:
            seller = request.user.seller
        except Exception:
            raise PermissionDenied(detail="you don't have a seller account")
        if not seller.is_verifed:
            return False
        return True

class HasEmail(BasePermission):
    """
    Allows access only to authenticated users.
    """

    def has_permission(self, request, view):
        if request.user.email in [None, ""]:
            raise PermissionDenied(detail="email is required")
        return True

class IsSeller(BasePermission):
    """
    Allows access only to authenticated users.
    """

    def has_permission(self, request, view):
        try:
            seller = request.user.seller
        except Exception:
            raise PermissionDenied(detail="you don't have a seller account")
        return True
    
class CanVerify(BasePermission):
    """
    Check if authenticated user is owner of the address
    """

    def has_permission(self, request, view):
        return request.user.has_perm('sellers.can_verify_seller') or request.user.is_staff