from django.utils.translation import gettext_lazy as _
from acl.classes import PermissionNamespace

namespace = PermissionNamespace()


# User
permission_user_list_view = namespace.add_permission(
    privilege_name='VIEW_USER_LIST',
    privilege_desc=_('Viewed all users list!'),
    module_id=40
)

permission_user_create = namespace.add_permission(
    privilege_name='CREATE_USER',
    privilege_desc=_('Created a new user successfully!'),
    module_id=40
)

permission_user_detail_view = namespace.add_permission(
    privilege_name='VIEW_USER',
    privilege_desc=_('Viewed user detail!'),
    module_id=40
)

permission_user_short_info = namespace.add_permission(
    privilege_name='VIEW_USER_SHORT_INFO_LIST', privilege_desc=_('Specific User short info viewed!'), module_id=60
)
permission_user_detail_edit = namespace.add_permission(
    privilege_name='UPDATE_USER',
    privilege_desc=_('User details updated successfully!'),
    module_id=40
)

permission_user_detail_delete = namespace.add_permission(
    privilege_name='DELETE_USER',
    privilege_desc=_('User details deleted successfully!'),
    module_id=40
)

permission_user_password_edit = namespace.add_permission(
    privilege_name='UPDATE_USER_PASSWORD',
    privilege_desc=_('User password updated successfully!'),
    module_id=40
)

permission_user_status_edit = namespace.add_permission(
    privilege_name='UPDATE_USER_STATUS',
    privilege_desc=_('User status updated successfully!'),
    module_id=40
)

