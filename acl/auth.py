from django.db import OperationalError, ProgrammingError
from .models import MasterPrivilege
from django.contrib.auth import get_user_model

User = get_user_model()


def create_permission(permission_list):
    for permission in permission_list:
        try:
            data = MasterPrivilege.objects.filter(
                privilege_name=permission.privilege_name,

            )
            if data.exists():
                data.update(privilege_name=permission.privilege_name, privilege_desc=permission.privilege_desc,
                            module_id=permission.module_id)

            else:
                MasterPrivilege.objects.create(
                    privilege_name=permission.privilege_name,
                    privilege_desc=permission.privilege_desc,
                    module_id=permission.module_id,
                )
        except (OperationalError, ProgrammingError):
            """
            This error is expected when trying to initialize the
            stored permissions during the initial creation of the
            database. Can be safely ignore under that situation.
            """
            break