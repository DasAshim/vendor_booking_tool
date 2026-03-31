from rest_framework.permissions import BasePermission
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException
from rest_framework.status import HTTP_401_UNAUTHORIZED
from .models import UserRole, RolePermission


class Unauthorized(APIException):
    status_code = HTTP_401_UNAUTHORIZED
    default_detail = 'Authentication credentials were not valid'
    default_code = 'Unauthorized'


def check_user_permissions(permissions, user):
    for permission in permissions:
        roles = UserRole.objects.filter(user=user).values_list("role", flat=True)
        if RolePermission.objects.filter(role__in=roles,
                                         privilege__privilege_name=permission.privilege_name).exists():
            return True
    raise PermissionDenied(_('Insufficient permissions.'))


class CozentusPermission(BasePermission):
    def has_permission(self, request, view):
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            raise Unauthorized()

        # Get required permissions for the specific HTTP method (GET, POST, etc.)
        required_permissions = getattr(
            view, 'vendor_booking_tool_object_permissions', {}
        ).get(request.method, None)

        # Check if the view has application privilege
        is_application_privilege = getattr(view, 'is_application_privilege', False)

        # If the request is from an application user and the view allows application privilege
        if is_application_privilege and request.user.is_application:
            return True

        if request.user.is_superuser:
            return True

        # If there are required permissions, check if the user has them
        if required_permissions:
            try:
                check_user_permissions(
                    permissions=required_permissions, user=request.user
                )
            except PermissionDenied:
                raise PermissionDenied({
                    "message": "You don't have permission to perform this task",
                })

        # If no required permissions or the check passed, return True
        return bool(required_permissions is None or request.user.is_authenticated)

