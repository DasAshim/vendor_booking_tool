import logging
import re

from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from django.core.validators import MinValueValidator
from datetime import timedelta, datetime, timezone
from vendor_booking_tool.utility import get_random_string
from acl.serializers import RoleShortInfoSerializer
from .models import User, TokenModule
from master_data_management.models import Company, UserCompany
from master_data_management.utility import get_company_info
from acl.models import (UserRole, Role, RolePermission, MasterPrivilege)
from .utility import create_user_in_auth0, update_user_in_auth0, check_user_exists_auth0


class UserSerializers(serializers.ModelSerializer):
    """
    This Serializer  defines how the user take input in the api
    """
    search = serializers.CharField(required=False, allow_blank=True)
    is_superuser = serializers.BooleanField(required=False, allow_null=True)
    page = serializers.IntegerField(required=False, allow_null=True)
    page_size = serializers.IntegerField(required=False, allow_null=True)
    email = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    first_name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    role_name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    country_code = serializers.CharField(max_length=4, required=False, allow_blank=True, allow_null=True)
    organisation_name = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    order_by = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True, write_only=True)
    order_type = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True,
                                       write_only=True)
    last_login_start_date = serializers.DateTimeField(allow_null=True, required=False)
    last_login_end_date = serializers.DateTimeField(allow_null=True, required=False)
    created_on_start_date = serializers.DateTimeField(allow_null=True, required=False)
    created_on_end_date = serializers.DateTimeField(allow_null=True, required=False)
    created_by = serializers.IntegerField(allow_null=True, required=False)
    created_by_name = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    modified_on_start_date = serializers.DateTimeField(allow_null=True, required=False)
    modified_on_end_date = serializers.DateTimeField(allow_null=True, required=False)
    modified_by = serializers.IntegerField(allow_null=True, required=False)
    modified_by_name = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    status = serializers.IntegerField(required=False, allow_null=True)
    export = serializers.BooleanField(required=False, allow_null=True, default=False)

    # auth0_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = User
        fields = ('email', 'is_superuser', 'first_name', 'last_name', 'organisation_name', 'country_code',
                  'phone_number', 'order_by', 'order_type', 'created_on_start_date', 'created_on_end_date',
                  'created_by', 'created_by_name', 'modified_on_start_date',
                  'modified_on_end_date', 'last_login_start_date', 'last_login_end_date', 'modified_by',
                  'modified_by_name', 'page', 'page_size', 'status', "role_name",
                  'export', 'search',)


class UserReadSerializer(serializers.ModelSerializer):
    """
    This serializer is used on the time of responding data for user
    """
    role_data = serializers.SerializerMethodField(source='get_role_data', read_only=True)

    class Meta:
        model = User
        fields = (
            "id", "is_superuser", "email", 'first_name', 'last_name', 'created_on', 'last_login', 'status',
            'country_code',
            'is_deleted', 'phone_number', 'modified_on', "last_login", "organisation_name", "timezone",
            "country", "created_by", "created_on", "modified_by", "modified_on", "role_data")

    @extend_schema_field(OpenApiTypes.ANY)
    def get_role_data(self, obj):
        """
        This method is used for getting role data as per the user
        """
        role = UserRole.objects.filter(user=obj).values_list('role', flat=True)
        if not role:
            return []
        return RoleShortInfoSerializer(Role.objects.filter(id__in=role), read_only=True, context=self.context,
                                       many=True).data


class UserProfileReadSerializer(serializers.ModelSerializer):
    """
    This serializer is used on the time of responding data for user
    """
    role = serializers.SerializerMethodField(source='get_role', read_only=True)
    company = serializers.SerializerMethodField(source='get_company', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'is_superuser', 'announcement_read_flag', 'role', 'email', 'first_name', 'last_name',
            'created_on', 'last_login', 'status', 'country_code', 'company',
            'is_deleted', 'phone_number', 'modified_on', "last_login", "organisation_name", "timezone",
            "country", "created_by", "modified_by")

    @extend_schema_field(OpenApiTypes.ANY)
    def get_role(self, obj):
        """
        This method is used for getting role data as per the user
        """
        role = UserRole.objects.filter(user=obj).values_list('role', flat=True)
        if not role:
            return []
        role_data = RoleShortInfoSerializer(Role.objects.filter(id__in=role), read_only=True, context=self.context,
                                            many=True).data
        return role_data

    @extend_schema_field(OpenApiTypes.ANY)
    def get_company(self, obj):
        """
        This method is used for getting company data as per the user
        """
        user_company = UserCompany.objects.filter(user=obj).first()
        if not user_company:
            return None

        company_dict = get_company_info()
        company_name = company_dict.get(user_company.company.id)
        if company_name:
            return {
                "id": user_company.company.id,
                "name": company_name
            }
        return None


class UserShortInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', "phone_number", 'country_code',)


class UserSerializer(serializers.ModelSerializer):
    """
    Register new user model serializer
    """

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone_number', 'email',
                  "organisation_name", "timezone", "country",)


class UserEditSerializer(serializers.ModelSerializer):
    """
    perform retrieve, update serializer for user
    """
    role_id = serializers.IntegerField(allow_null=True, required=False)
    company_id = serializers.IntegerField(allow_null=True, required=False, write_only=True)
    role = serializers.SerializerMethodField(read_only=True)
    company_dict = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('status', 'role_id', 'first_name', 'last_name', 'phone_number', 'email',
                  "organisation_name", "timezone", "country", 'country_code', 'company_id', 'company_dict', 'role',
                  )
        read_only_fields = ('company_dict',)

    def update(self, instance, validated_data):
        try:
            new_email = validated_data.get('email').lower()
            new_first_name = validated_data.get('first_name')
            new_last_name = validated_data.get('last_name')

            if new_email:
                validated_data['email'] = new_email.strip().lower()
                new_email = validated_data['email']

                # Determine if we need to call Auth0
            email_changed = new_email and new_email.lower() != instance.email.lower()
            first_name_changed = new_first_name is not None and new_first_name != instance.first_name
            last_name_changed = new_last_name is not None and new_last_name != instance.last_name

            if email_changed or first_name_changed or last_name_changed:
                request = self.context.get('request')
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')

                if not auth_header.startswith('Bearer '):
                    raise serializers.ValidationError({
                        'message': 'Valid authorization token is required'
                    })

                # Build the Auth0 update payload with only changed fields
                auth0_updates = {}

                if email_changed:
                    auth0_updates['email'] = new_email
                    auth0_updates['email_verified'] = False
                    auth0_updates['verify_email'] = True

                if first_name_changed:
                    auth0_updates['given_name'] = new_first_name

                if last_name_changed:
                    auth0_updates['family_name'] = new_last_name

                try:
                    update_user_in_auth0(
                        lookup_email=instance.email,
                        auth0_updates=auth0_updates
                    )
                    logging.info(f"Auth0 updated successfully for user {instance.id}")
                except Exception as e:
                    logging.error(f"Failed to update Auth0 for user {instance.id}: {str(e)}")
                    raise serializers.ValidationError({
                        'message': f'Failed to update Auth0: {str(e)}'
                    })
            role_id = validated_data.pop("role_id", None)
            company_id = validated_data.pop("company_id", None)

            if role_id:
                role_instance = Role.objects.get(id=role_id)
                if not role_instance:
                    raise serializers.ValidationError(detail='Pls provide valid role', code=400)
                UserRole.objects.update_or_create(
                    user=instance,
                    defaults={
                        "role": role_instance,
                        "created_by": self.context['request'].user.id
                    }
                )

            if "company_id" in self.initial_data:
                if company_id is None:
                    UserCompany.objects.filter(user=instance).delete()
                else:
                    company_instance = Company.objects.filter(id=company_id).first()
                    if not company_instance:
                        raise serializers.ValidationError(detail='Please provide a valid company', code=400)

                    user_company = UserCompany.objects.filter(user=instance).first()

                    if user_company:
                        if user_company.company_id != company_id:
                            user_company.company = company_instance
                            user_company.save()
                    else:
                        UserCompany.objects.create(user=instance, company=company_instance)

            instance = super().update(instance, validated_data)
            return instance
        except serializers.ValidationError as e:
            raise serializers.ValidationError({'message': e.detail.get('message')})
        except Exception as e:
            raise serializers.ValidationError({'message': str(e)})

    def get_company_dict(self, obj):
        """
        Return company name using the utility function.
        """
        try:
            user_company = UserCompany.objects.filter(user=obj).first()
            if not user_company:
                return None
            company_dict = get_company_info()
            company_name = company_dict.get(user_company.company.id)
            if company_name:
                return {
                    "id": user_company.company.id,
                    "name": company_name
                }
            return None
        except Exception as e:
            logging.error(f"Error in get_company_dict: {e}", exc_info=True)
            return None

    def get_role(self, obj):
        user_role = UserRole.objects.filter(user=obj).first()
        return user_role.role.id if user_role else None


class UserReadEmailSerializer(serializers.ModelSerializer):
    """
    Read user email model serializer
    """

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name",)


class TokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenModule
        fields = ("id", "user_id", "expiry_days", "expiry_time", "primary_token", "type",
                  "created_by", "created_on", "modified_by", "modified_on")
        read_only_fields = (
            "id", "primary_token", "expiry_time", "created_by", "created_on", "modified_by", "modified_on")

    def create(self, validated_data):
        validated_data["primary_token"] = get_random_string(length=120)
        expiry_days = validated_data.get("expiry_days")
        start_time = datetime.now(timezone.utc)
        expiry_time = start_time + timedelta(days=expiry_days)
        validated_data["expiry_time"] = expiry_time
        instance = super().create(validated_data)

        return instance


class TokenReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenModule
        fields = '__all__'


class ResetTokenSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    expiry_days = serializers.IntegerField(required=False, min_value=1)


class UpdateSuperUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('is_superuser',)

    def validate(self, validated_data):
        user = self.context['request'].user  # Get the requesting user
        user_id = self.context['view'].kwargs.get('pk')  # Get the ID from URL arguments

        # Prevent users from modifying their own superuser status
        if user.id == int(user_id) and validated_data.get('is_superuser') is not None:
            raise serializers.ValidationError("You cannot change your own superuser status.")

        # Non-superusers cannot modify the 'is_superuser' field
        if not user.is_superuser and validated_data.get('is_superuser') is not None:
            raise serializers.ValidationError('Only superusers are allowed to update superuser status.')

        # Remove the 'is_superuser' field from validated data if the user is not a superuser
        validated_data.pop('is_superuser', None) if not user.is_superuser else None

        return validated_data


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('status', 'first_name', 'last_name', 'email', 'password', 'organisation_name', 'created_on',
                  )
        read_only_fields = ('created_on',)

    def create(self, validated_data):
        try:
            with transaction.atomic():
                password = validated_data.pop('password')

                user = User.objects.create_user(
                    password=password,
                    **validated_data)

                return user

        except Exception as ee:
            logging.error(ee)
            raise serializers.ValidationError("Please provide valid data")


class UserRoleSerializer(serializers.ModelSerializer):
    role = serializers.IntegerField(write_only=True)
    company = serializers.IntegerField(write_only=True, allow_null=True)
    company_dict = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'status', 'first_name', 'last_name', 'email', 'organisation_name', 'role', 'company',
                  'company_dict', 'created_on',)
        read_only_fields = ('created_on', 'id', 'company_dict')

    @staticmethod
    @extend_schema_field(OpenApiTypes.ANY)
    def validate_role(role_id):
        role = Role.objects.filter(id=role_id).first()
        if not role:
            raise serializers.ValidationError('Please provide a valid role')
        return role

    def create(self, validated_data):
        try:
            with transaction.atomic():
                role_data = validated_data.pop('role', None)
                company_id = validated_data.pop('company', None)

                # Always use create_user or create_superuser
                if validated_data.get("is_superuser", False):
                    user = User.objects.create_superuser(
                        **validated_data
                    )
                else:
                    email = validated_data.get("email").strip().lower()
                    auth0_user_id = None
                    password = validated_data.get("password")

                    # First, check if user already exists in Auth0
                    try:
                        user = User.objects.get(email=email)
                        logging.info(f"User already exists in Auth0 with EMAIL: {user.email}")
                    except (ValueError, Exception) as e:
                        # User doesn't exist in Auth0, create new one
                        logging.info(f"User not found in DB , creating new user: {str(e)}")

                        user = User.objects.create_user(
                            **validated_data
                        )

                    if role_data:
                        UserRole.objects.create(user=user, role=role_data)

                    if company_id:
                        self.add_user_company(user.id, company_id)

                return user

        except serializers.ValidationError:
            raise
        except Exception as ee:
            logging.exception("User creation failed")
            raise serializers.ValidationError(str(ee))

    def update(self, instance, validated_data):
        try:
            with transaction.atomic():
                role_data = validated_data.pop('role', None)
                password = validated_data.pop('password', None)

                email = validated_data.get("email", instance.email).strip().lower()

                # Step 1: Get Auth0 user (currently DB check)
                auth0_users = User.objects.filter(email=email)

                if not auth0_users:
                    raise serializers.ValidationError("User not found in Auth0.")

                #  If only role update (no other fields, no password)
                if not validated_data and not password and role_data:
                    UserRole.objects.filter(user=instance).delete()
                    UserRole.objects.create(user=instance, role=role_data)
                    return instance

                #  xxxxFULL UPDATE (DB LOGIN FLOW)
                if not validated_data and not password and not role_data:
                    raise serializers.ValidationError(
                        "Please provide at least one field to update."
                    )

                # Update fields
                for attr, value in validated_data.items():
                    setattr(instance, attr, value)

                # Update password (hashed)
                if password:
                    instance.set_password(password)

                instance.save()

                # Update role if provided
                if role_data:
                    UserRole.objects.filter(user=instance).delete()
                    UserRole.objects.create(user=instance, role=role_data)

                return instance

        except serializers.ValidationError:
            raise

        except Exception as ee:
            logging.error(ee)
            raise serializers.ValidationError("Please provide valid data")


# def update(self, instance, validated_data):
#     try:
#         with transaction.atomic():
#             role_data = validated_data.pop('role', None)
#             password = validated_data.pop('password', None)
#
#             email = validated_data.get("email", instance.email).strip().lower()
#
#             #  Step 1: Get Auth0 user
#             auth0_users = check_user_exists_auth0(email)
#
#             connection = None
#             if auth0_users:
#                 connection = auth0_users[0].get("connection")
#                 print('connection', connection)
#
#             #  Step 2: Restrict updates based on connection
#             restricted_fields = {"first_name", "last_name", "email"}
#
#             if connection and connection != "Username-Password-Authentication":
#                 #  Allow ONLY role update
#                 if any(field in validated_data for field in restricted_fields):
#                     raise serializers.ValidationError(
#                         "Cannot update name/email for social login users. Only role can be updated."
#                     )
#
#             for attr, value in validated_data.items():
#                 setattr(instance, attr, value)
#
#             if password:  # Hash it properly
#                 instance.set_password(password)
#
#             instance.save()
#
#             if role_data:
#                 UserRole.objects.filter(user=instance).delete()
#                 UserRole.objects.create(user=instance, role=role_data)
#
#             return instance
#
#     except Exception as ee:
#         logging.error(ee)
#         raise serializers.ValidationError("Please provide valid data")

@staticmethod
def add_user_company(user_id, company_id):
    """
        Assign user a company
    """
    try:
        with transaction.atomic():
            # validate user and company existence
            user = User.objects.filter(id=user_id).first()
            company = Company.objects.filter(id=company_id).first()

            if not user or not company:
                raise serializers.ValidationError(
                    {"message": f"Invalid user ({user_id}) or company ({company_id})"}
                )

            if UserCompany.objects.filter(user=user, company=company).exists():
                raise serializers.ValidationError(
                    {"message": "This user is already linked to the selected company."}
                )

            if UserCompany.objects.filter(user=user).exclude(company=company).exists():
                raise serializers.ValidationError(
                    {"message": "This user is already linked to another company."}
                )

            user_company = UserCompany.objects.create(
                user=user,
                company=company,
            )

            return user_company
    except Exception as e:
        raise serializers.ValidationError(
            {"message": "Please provide valid user data or company data", "error": str(e)}
        )

    def get_company_dict(self, obj):
        """
        Return company name using the utility function.
        """
        try:
            user_company = UserCompany.objects.filter(user=obj).first()
            if not user_company:
                return None
            company_dict = get_company_info()
            company_name = company_dict.get(user_company.company.id)
            if company_name:
                return {
                    "id": user_company.company.id,
                    "name": company_name
                }
            return None
        except Exception as e:
            logging.error(f"Error in get_company_dict: {e}", exc_info=True)
            return None


class RolePrivilegeSerializer(serializers.ModelSerializer):
    """
    Serializer to return role_id and associated privileges.
    """
    user_id = serializers.IntegerField(required=False)
    privilege_names = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ('user_id', 'privilege_names')

    @staticmethod
    @extend_schema_field(OpenApiTypes.ANY)
    def get_privilege_names(obj):
        privilege_ids = RolePermission.objects.filter(role=obj).values_list('privilege_id', flat=True)
        return list(MasterPrivilege.objects.filter(id__in=privilege_ids).values_list('privilege_name', flat=True))
