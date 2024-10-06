from rest_framework.permissions import BasePermission
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
user = get_user_model()
class IsUserProfileOwner(BasePermission):
    """
    Check if authenticated user is owner of the profile
    """

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_staff


class IsUserAddressOwner(BasePermission):
    """
    Check if authenticated user is owner of the address
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated is True

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_staff

class ResetPassword(BasePermission):
    def has_permission(self, request, view):
        try:
            return request.user.passwordreset.password_expiration >= timezone.now()
        except Exception:
            raise PermissionDenied(detail="u did not issue a reset password request")