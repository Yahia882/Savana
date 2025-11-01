
from rest_framework.permissions import BasePermission
from django.contrib.auth.models import User
class CanReview(BasePermission):
    """
    Check if authenticated user is owner of the address
    """

    def has_permission(self, request, view):

        return request.user.has_perm('sellers.can_change_status') or request.user.is_staff