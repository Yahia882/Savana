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
    
class HasVariations(BasePermission):
    """
    Check if the seller has added variations to the product identity
    """

    def has_permission(self, request, view):
        try:
            has_variation = request.user.seller.draft_data['tmp']["ProductIdentity"].get("has_variations")
        except (KeyError, ObjectDoesNotExist):
            raise PermissionDenied(detail="you need to set product identity first")
        if not has_variation:
            raise PermissionDenied(detail="you set the product identity as having no variations")
        return True
    
class HasNoVariations(BasePermission):
    """
    Check if the seller has added variations to the product identity
    """

    def has_permission(self, request, view):
        try:
            has_variation = request.user.seller.draft_data['tmp']["ProductIdentity"].get("has_variations")
        except (KeyError, ObjectDoesNotExist):
            raise PermissionDenied(detail="you need to set product identity first")
        if has_variation:
            raise PermissionDenied(detail="you set the product identity as having variations")
        return True
    
class ProductInfoCollected(BasePermission):
    """
    Check if the seller has added all the product info to publish the product
    """

    def has_permission(self, request, view):
        data = {}
        if request.data.get("draft_name"):
            data = request.user.seller.draft_data.get('draft_products',None).get(request.data["draft_name"],{})
        else:
            data = request.user.seller.draft_data.get('tmp',{})
        if data == {} or data is None:
            raise PermissionDenied(detail="Please enter product info.")
        if data.get("ProductIdentity",None) in [None, ""]:
            raise PermissionDenied(detail="Please enter product identity.")
        if data["ProductIdentity"].get("product_description",None) in [None, ""]:
            raise PermissionDenied(detail="Please enter product description.")
        if data["ProductIdentity"].get("product_details",None) in [None, ""]:
            raise PermissionDenied(detail="Please enter product details.")
        if data.get("actual_variations",None) in [None, ""]:
            if data["ProductIdentity"]["has_variations"]:
                raise PermissionDenied(detail="Please enter product variations offers.")
            else:
                raise PermissionDenied(detail="Please enter product offer.")
        return True