import datetime
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import OuterRef
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status, serializers
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView, GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

# from master_data_management.utility import build_role_global_search_q
from vendor_booking_tool.utility import apply_date_time_range_filters
from user_management.utility import return_user_id_by_name
from .export_excel import export_query_to_excel
from .permissions import permission_role_list, permission_role_create, permission_role_view, permission_role_edit, \
    permission_role_delete, permission_permission_list
from .serializers import (RoleMultiUserCreateSerializer, RoleFilterSerializer, RoleReadSerializer,
                          RoleReadWithoutPrivilegeSerializer, RoleSerializer, RolePermissionFilterSerializer,
                          PermissionSerializer)
from django.core.paginator import Paginator
from .models import Role, UserRole, MasterPrivilege, RolePermission
from .privilege import CozentusPermission

User = get_user_model()


class RoleFilterApi(APIView):
    """
    This view class is used to return  roles with filter and pagination
    """
    # vendor_booking_tool_object_permissions = {
    #     'POST': (permission_role_list,)
    # }
    # permission_classes = (CozentusPermission,)
    serializer_class = RoleReadSerializer

    @extend_schema(request=RoleFilterSerializer)
    def post(self, request):
        """
        This method is used to make post request for pagination and filter and return the role data.
        """
        serializer = RoleFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        try:
            page_size = data.get("page_size", 50) if data.get("page_size") is not None else 50
            page = data.get("page", 1) if data.get("page") is not None else 1
            if page < 1 or page_size < 1:
                return Response({"message": "page and page size should be positive integer"},
                                status=status.HTTP_400_BAD_REQUEST)
            order_by = data.get('order_by')
            order_type = data.get('order_type')
            module_id = data.get('module_id', None)
            include_privilege_data = data.pop('include_privilege_data', True)

            filter_dict = {
                "role_name": "role_name__icontains", "role_description": "role_description__icontains",
                "created_by": "created_by", "created_on": "created_on", "modified_by": "modified_by",
                "modified_on": "modified_on"
            }

            dict_ = {filter_dict.get(key, None): value for key, value in data.items() if
                     value or isinstance(value, int)}
            dict_ = {key: value for key, value in dict_.items() if key}

            roles = Role.objects.filter(**dict_)
            roles = apply_date_time_range_filters(roles, data)

            # Build global search Q only if search has value
            search_value = data.get("search")
            # if search_value:
            #     roles = roles.filter(build_role_global_search_q(search_value))

            created_by_name = data.get("created_by_name")
            modified_by_name = data.get("modified_by_name")
            if created_by_name:
                user_ids = return_user_id_by_name(created_by_name)
                roles = roles.filter(created_by__in=user_ids)
            if modified_by_name:
                user_ids = return_user_id_by_name(modified_by_name)
                roles = roles.filter(modified_by__in=user_ids)

            if order_by == "created_by":
                roles = roles.annotate(
                    created_by_name=User.objects.filter(id=OuterRef('created_by')).values(
                        'first_name')[:1])
            elif order_by == "modified_by":
                roles = roles.annotate(
                    modified_by_name=User.objects.filter(id=OuterRef('modified_by')).values(
                        'first_name')[:1])

            order_by_dict = {
                "role_name": "role_name", "role_description": "role_description", "created_by": "created_by_name",
                "created_on": "created_on", "modified_on": "modified_on", "modified_by": "modified_by_name"
            }
            query_filter = order_by_dict.get(order_by, None)

            if order_type == "desc" and query_filter:
                query_filter = f"-{query_filter}"
            if query_filter:
                roles = roles.order_by(query_filter)
            if data.get("export") and module_id:
                results = RoleReadSerializer(roles, many=True)
                return export_query_to_excel(data=results.data, module_name="ROLE_MANAGEMENT")
            # Create Paginator object with page_size objects per page
            paginator = Paginator(roles, page_size)
            number_pages = paginator.num_pages
            if page > number_pages and page > 1:
                return Response({"message": "Page not found"}, status=status.HTTP_400_BAD_REQUEST)
            # Get the page object for the requested page number
            page_obj = paginator.get_page(page)
            if include_privilege_data:
                results = RoleReadSerializer(page_obj, many=True)
            else:
                results = RoleReadWithoutPrivilegeSerializer(page_obj, many=True)
            return Response({'count': roles.count(), 'results': results.data}, status=status.HTTP_200_OK)
        except serializers.ValidationError as ve:
            raise serializers.ValidationError(ve.detail)
        except Exception as ee:
            return Response(str(ee), status=status.HTTP_400_BAD_REQUEST)


class RoleCreateApi(CreateAPIView):
    """
    This view class is used to Create a new role
    """
    vendor_booking_tool_object_permissions = {
        'POST': (permission_role_create,)
    }
    permission_classes = (CozentusPermission,)
    serializer_class = RoleSerializer
    queryset = Role.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id)


class RoleUpdateApi(RetrieveUpdateDestroyAPIView):
    """
    This view class is used to update an existing role
    """
    vendor_booking_tool_object_permissions = {
        'GET': (permission_role_list,),
        'PUT': (permission_role_edit,),
        'PATCH': (permission_role_edit,),
        'DELETE': (permission_role_delete,)
    }
    permission_classes = (CozentusPermission,)
    serializer_class = RoleSerializer
    queryset = Role.objects.all()

    def get_serializer_class(self):
        """Return Read serializer for GET"""
        if self.request.method == "GET":
            return RoleReadSerializer
        return RoleSerializer

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user.id,
                        modified_on=timezone.now().astimezone(timezone.timezone.utc))

    def perform_destroy(self, instance):
        if User.objects.filter(
                id__in=UserRole.objects.filter(role=instance).values_list('user_id', flat=True),
                is_deleted=0).exists():
            raise ValidationError({"message": "This Role is currently associated with Single/Multiple Users!"})
        instance.delete()


class RolePermissionFilterApi(APIView):
    permission_classes = (CozentusPermission,)
    serializer_class = RolePermissionFilterSerializer

    @extend_schema(request=RolePermissionFilterSerializer)
    def post(self, request):
        serializer = RolePermissionFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            page_size = data.get("page_size") or 200
            page = data.get("page") or 1
            if page < 1 or page_size < 1:
                return Response({"message": "page and page size should be positive integer"},
                                status=status.HTTP_400_BAD_REQUEST)

            privilege_name = data.get('privilege_name')
            privilege_desc = data.get('privilege_desc')
            role_id = data.get('role_id')
            order_by = data.get('order_by')
            order_type = data.get('order_type')

            queryset = MasterPrivilege.objects.all()
            if role_id:
                role_permission = RolePermission.objects.filter(role__id=role_id).values_list("privilege", flat=True)
                queryset = queryset.filter(id__in=role_permission)
            if privilege_name:
                queryset = queryset.filter(privilege_name__icontains=privilege_name)
            if privilege_desc:
                queryset = queryset.filter(privilege_desc__icontains=privilege_desc)

            if order_by in ["privilege_name", "privilege_desc"]:
                if order_type == "desc":
                    order_by = f"-{order_by}"
                queryset = queryset.order_by(order_by)

            module_id = request.data.get('module_id')
            if request.data.get("export") and module_id:
                results = PermissionSerializer(queryset, many=True)
                return export_query_to_excel(data=results.data, module_name="ROLE_PERMISSION", module_id=module_id)

            paginator = Paginator(queryset, page_size)
            if page > paginator.num_pages:
                return Response({"message": "Page not found"}, status=status.HTTP_400_BAD_REQUEST)

            page_obj = paginator.get_page(page)
            serialized = PermissionSerializer(page_obj, many=True).data

            # ✅ Group by module_id
            grouped = defaultdict(list)
            for item in serialized:
                grouped[item["module_id"]].append({
                    "id": item["id"],
                    "privilege_name": item["privilege_name"],
                    "privilege_desc": item["privilege_desc"],
                })

            response_data = [
                {"module_id": module_id, "privileges": privileges}
                for module_id, privileges in grouped.items()
            ]

            return Response({"count": queryset.count(), "results": response_data})

        except serializers.ValidationError as ve:
            return Response({"message": ve.detail, "error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as ee:
            return Response({"message": "Something went wrong", "error": str(ee)},
                            status=status.HTTP_400_BAD_REQUEST)


class RoleUserCreateAPI(CreateAPIView):
    """
    This view class is used to assign user a role
    """
    # vendor_booking_tool_object_permissions = {
    #     'POST': (permission_role_user_create,)
    # }
    permission_classes = (CozentusPermission,)
    serializer_class = RoleMultiUserCreateSerializer

    @extend_schema(request=RoleMultiUserCreateSerializer)
    def post(self, request):
        """
        This method is used for retrieving role permission data with pagination and filter
        """
        serializer = RoleMultiUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        try:

            user_ids = data.get("user_ids", [])
            role_id = data.get("role_id", "")
            updated_data = []
            role_object = Role.objects.filter(id=role_id).first()
            if not role_object:
                raise ValidationError({"message": "Invalid role_id"}, code=status.HTTP_400_BAD_REQUEST)

            role_user_list = UserRole.objects.filter(role=role_object).values_list("user", flat=True)
            first_set = set(role_user_list)
            second_set = set(user_ids)
            remove_user = first_set - second_set
            add_user = second_set - first_set
            with transaction.atomic():
                UserRole.objects.filter(user_id__in=user_ids).exclude(role_id=role_id)
                if remove_user:
                    UserRole.objects.filter(user__id__in=list(remove_user)).delete()
                for user_id in list(add_user):
                    updated_data.append(UserRole(role=role_object,
                                                 user=User.objects.filter(id=user_id).first()))
                if updated_data:
                    UserRole.objects.bulk_create(updated_data)

            return Response({"results": data}, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as ve:
            return Response({"message": ve.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as ee:
            return Response({"message": "Please provide valid user data or role data", "error": str(ee)},
                            status=status.HTTP_400_BAD_REQUEST)
