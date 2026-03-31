import logging

logger = logging.getLogger(name="CARGO_PLAN")


class PermissionNamespace:
    def __init__(self):
        self.permissions = []

    def add_permission(self, privilege_name, privilege_desc, module_id=""):
        permission = Permission(privilege_name=privilege_name, privilege_desc=privilege_desc,
                                module_id=module_id)
        self.permissions.append(permission)
        return permission


class Permission:

    def __init__(self, privilege_name, privilege_desc, module_id):
        self.privilege_name = privilege_name
        self.privilege_desc = privilege_desc
        self.module_id = module_id
        self.pk = self.get_pk()

    def get_pk(self):
        return self.privilege_name
