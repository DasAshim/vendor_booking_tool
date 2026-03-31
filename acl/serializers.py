import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.core.validators import MinValueValidator

from acl.models import RolePermission, Role, MasterPrivilege

User = get_user_model()


class RolePermissionSerializer(serializers.ModelSerializer):
    """
    This serializer is used for retrieving role permission
    """
    privilege_name = serializers.CharField(source='privilege.privilege_name')
    privilege_desc = serializers.CharField(source='privilege.privilege_desc')

    class Meta:
        model = RolePermission
        fields = ("id", "privilege_name", 'privilege_desc')


class RoleReadSerializer(serializers.ModelSerializer):
    """
    This serializer is used for response data of role
    """
    privilege_names = serializers.SerializerMethodField(source='get_privilege_names', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    modified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = (
            "id","role_name", "role_description","privilege_names",
            "modified_on", "modified_by", "created_on", "created_by", "created_by_name", "modified_by_name")

    @staticmethod
    @extend_schema_field(OpenApiTypes.ANY)
    def get_privilege_names(obj):
        permissions = RolePermission.objects.filter(role=obj).values_list("privilege", flat=True)
        return MasterPrivilege.objects.filter(id__in=permissions).values_list('privilege_name', flat=True)

    @extend_schema_field(OpenApiTypes.ANY)
    def get_created_by_name(self, obj):
        user = User.objects.filter(id=obj.created_by).first()
        return user.first_name if user else None

    @extend_schema_field(OpenApiTypes.ANY)
    def get_modified_by_name(self, obj):
        user = User.objects.filter(id=obj.modified_by).first()
        return user.first_name if user else None


class RoleReadWithoutPrivilegeSerializer(serializers.ModelSerializer):
    """
    This serializer is used for response data of role
    """

    class Meta:
        model = Role
        fields = (
            "id","role_name", "role_description","modified_on", "modified_by",
            "created_on", "created_by")


class RoleShortInfoSerializer(serializers.ModelSerializer):
    """
        This serializer is used for response data of role
        """

    class Meta:
        model = Role
        fields = ("id","role_name")


class RoleSerializer(serializers.ModelSerializer):
    """
    This serializer is used for create and update the role
    """
    privilege_names = serializers.ListField(child=serializers.CharField(), write_only=True)
    role_name = serializers.CharField()
    role_description = serializers.CharField(max_length=1000, required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Role
        fields = ("id","role_name", "role_description", "privilege_names")

    def create(self, validate_data):
        """
        This is a Create method for Role Create
        It takes role id, role name, role description, privilege id and return the Role object and privilege ids
        if everything is right otherwise it will return error
        """
        try:
            """
             Validate that the role_name is unique.
            """

            role_name = validate_data.get('role_name')

            # Check if a Role with the same role_name already exists
            if Role.objects.filter(role_name=role_name).exists():
                raise serializers.ValidationError(
                    "A role with this role name already exists.")
            privilege_names = validate_data.pop("privilege_names", [])
            with transaction.atomic():
                instance = Role.objects.create(role_name=role_name,
                                               role_description=validate_data.get("role_description"),
                                               created_by=validate_data.get("created_by"))

                if MasterPrivilege.objects.filter(privilege_name__in=privilege_names).count() != len(
                        set(privilege_names)):
                    raise serializers.ValidationError("please provide valid privilege")
                for privilege_name in privilege_names:
                    privilege = MasterPrivilege.objects.filter(privilege_name=privilege_name).first()
                    RolePermission.objects.create(privilege=privilege, role=instance,
                                                  created_by=validate_data.get("created_by"))
                instance.save()
                return instance
        except serializers.ValidationError as ve:
            raise serializers.ValidationError(ve.detail)
        except Exception as ee:
            logging.info(ee)
            raise serializers.ValidationError("Role name must be unique.")

    def update(self, instance, validate_data):
        """
        This is an Update method for Role Update
        It takes role id, role name, role description, privilege id and return the Role object and privilege ids
        if everything is right otherwise it will return error
        """
        try:
            privilege_names = validate_data.get('privilege_names', [])
            record = instance
            """
            Validate that the role_name is unique.
            """

            role_name = validate_data.get('role_name')
            # Check if a Role with the same role_name already exists
            if Role.objects.filter(role_name=role_name).exclude(id=instance.id).exists():
                raise serializers.ValidationError(
                    "A role with this role name already exists.")

            if MasterPrivilege.objects.filter(privilege_name__in=privilege_names).count() != len(set(privilege_names)):
                raise serializers.ValidationError("please provide valid privilege")
            role_data = RolePermission.objects.filter(role=record).values_list("privilege__privilege_name", flat=True)
            with transaction.atomic():
                role_data = list(role_data)
                role_data.sort()
                privilege_names.sort()
                if role_data != privilege_names:
                    RolePermission.objects.filter(role=record).delete()
                    for privilege_name in privilege_names:
                        privilege = MasterPrivilege.objects.filter(privilege_name=privilege_name).first()
                        RolePermission.objects.create(privilege=privilege, role=instance,
                                                      created_by=validate_data.get("modified_by"))
                record.role_name = validate_data.get('role_name')
                record.role_description = validate_data.get('role_description')
                record.modified_by = validate_data.get('modified_by')
                record.modified_on = timezone.now().astimezone(timezone.timezone.utc)
                record.save()
                return record
        except serializers.ValidationError as ve:
            raise serializers.ValidationError(ve.detail)
        except Exception:
            raise serializers.ValidationError("Please provide Valid Role and privilege data")


class RoleFilterSerializer(serializers.ModelSerializer):
    """
    This serializer is used for role filter
    """
    search = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    role_name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    role_description = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    include_privilege_data = serializers.BooleanField(default=False, required=False, allow_null=True)
    order_by = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    order_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    created_on_start_date = serializers.DateTimeField(required=False, allow_null=True)
    created_by = serializers.IntegerField(required=False, allow_null=True)
    modified_by = serializers.IntegerField(required=False, allow_null=True)
    created_by_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    created_on_end_date = serializers.DateTimeField(required=False, allow_null=True)
    modified_by_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    modified_on_start_date = serializers.DateTimeField(required=False, allow_null=True)
    modified_on_end_date = serializers.DateTimeField(required=False, allow_null=True)
    page = serializers.IntegerField(required=False, allow_null=True, validators=[MinValueValidator(1)])
    page_size = serializers.IntegerField(required=False, allow_null=True, validators=[MinValueValidator(1)])
    export = serializers.BooleanField(required=False, allow_null=True, default=False)
    module_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Role
        fields = ('role_name', 'role_description', 'include_privilege_data', 'order_by', 'created_by',
                  'created_on_start_date',
                  'created_on_end_date', 'modified_on_start_date', 'modified_on_end_date', 'created_by_name',
                  'modified_by',
                  'modified_by_name', "export", 'module_id',
                  'order_type', 'page', 'page_size', 'search')


class RolePermissionFilterSerializer(serializers.ModelSerializer):
    """
    This serializer is used for making post request for  role permission
    """

    privilege_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    privilege_desc = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    role_id = serializers.IntegerField(required=False, allow_null=True)
    order_by = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    order_type = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    page = serializers.IntegerField(required=False, allow_null=True, validators=[MinValueValidator(1)])
    page_size = serializers.IntegerField(required=False, allow_null=True, validators=[MinValueValidator(1)])

    class Meta:
        model = RolePermission
        fields = ('privilege_name', 'privilege_desc', 'role_id', 'order_by', 'order_type', 'page', 'page_size')


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasterPrivilege
        fields = ("id", "privilege_name", "privilege_desc", "module_id")


class RoleMultiUserCreateSerializer(serializers.Serializer):
    role_id = serializers.CharField(max_length=100)
    user_ids = serializers.ListField(child=serializers.IntegerField(), required=True)
