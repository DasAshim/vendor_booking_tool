import logging
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from vendor_booking_tool.utility import BaseUserModel

User = get_user_model()
logger = logging.getLogger(name="VENDOR_BOOKING_TOOL")


class Role(BaseUserModel):
    """
    Role table
    """
    role_name = models.CharField(max_length=50, db_column="ROLE_NAME")
    role_description = models.CharField(max_length=1000, db_column="ROLE_DESC", null=True, blank=True)

    class Meta:
        ordering = ['-created_on']
        db_table = "ROLE"


class UserRole(BaseUserModel):
    """
    Role Add to user
    """
    modified_by = None
    modified_on = None
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="role_user", db_column="USER_ID")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_role_role", db_column="ROLE_ID")

    class Meta:
        ordering = ['-created_on']
        db_table = "USER_ROLE"


class MasterPrivilege(models.Model):
    """
    Master Privilege table
    """
    privilege_name = models.CharField(max_length=50, verbose_name=_('Privilege'), unique=True, db_column="PRIVILEGE_NAME")
    privilege_desc = models.CharField(max_length=1000, verbose_name=_('Privilege Description'), db_column="PRIVILEGE_DESC")
    module_id = models.CharField(max_length=1000, verbose_name=_('Module Id'), db_column="MODULE_ID")
    objects = models.Manager()

    class Meta:
        ordering = ('privilege_name',)
        db_table = "MASTER_PRIVILEGE"


class RolePermission(BaseUserModel):
    """
    Role Permission creation
    """
    modified_on = None
    modified_by = None
    privilege = models.ForeignKey(MasterPrivilege, on_delete=models.CASCADE,
                                  related_name="role_permission", db_column='PRIVILEGE_ID')
    role = models.ForeignKey(Role, on_delete=models.CASCADE,
                             related_name="role_permission_role", db_column='ROLE_ID')

    class Meta:
        ordering = ['-created_on']
        db_table = "ROLE_PRIVILEGE"



