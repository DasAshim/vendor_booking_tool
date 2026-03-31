import base64
from django.core.paginator import Paginator
from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (RetrieveAPIView, get_object_or_404, RetrieveUpdateDestroyAPIView,
                                     DestroyAPIView, CreateAPIView, UpdateAPIView, GenericAPIView)

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response

from acl.export_excel import export_query_to_excel
from acl.models import Role, RolePermission, UserRole
from vendor_booking_tool.utility import apply_date_time_range_filters

from .permissions import (permission_user_list_view,
                          permission_user_short_info, permission_user_detail_edit,
                          permission_user_detail_delete, permission_user_create)
from acl.privilege import CozentusPermission
from .serializers import (UserSerializers, UserReadSerializer, UserShortInfoSerializer,
                          UserEditSerializer, UserProfileReadSerializer,
                          TokenSerializer, ResetTokenSerializer, TokenReadSerializer, UpdateSuperUserSerializer,
                          UserRoleSerializer, UserRegisterSerializer)
from .models import User, TokenModule
from datetime import datetime, timedelta, timezone

from .utility import return_user_id_by_name, build_user_global_search_q


class UserFilterApi(APIView):
    """
    This view class is used to return user details with filter and pagination
    """
    serializer_class = UserReadSerializer
    vendor_booking_tool_object_permissions = {
        'POST': (permission_user_list_view,)
    }

    permission_classes = (CozentusPermission,)

    @extend_schema(request=UserSerializers)
    def post(self, request):
        """
        This method takes body input and filter the data and return the data with pagination
        """
        serializer = UserSerializers(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        try:
            page_size = data.get("page_size", 50) if data.get("page_size") is not None else 50
            page = data.get("page", 1) if data.get("page") is not None else 1
            if page < 1 or page_size < 1:
                return Response({"message": "page and page size should be positive integer"},
                                status=status.HTTP_400_BAD_REQUEST)
            order_by = request.data.get('order_by', None)
            order_type = request.data.get('order_type', None)
            application_id = request.data.get("application_id", None)

            user_status = data.get('status', None)
            filter_dict = {
                "is_superuser": "is_superuser",
                "email": "email__icontains",
                "first_name": "first_name__icontains",
                "last_name": "last_name__icontains",
                "organisation_name": "organisation_name__icontains",
                "phone_number": "phone_number__icontains",
                "status": "status",
                'country_code': 'country_code__icontains',
                "created_on": "created_on",
                "last_login": "last_login",
                "modified_by": "modified_by",
                "modified_on": "modified_on",
                "created_by": "created_by",
                "role_name": "role_user__role__role_name__icontains"
            }
            query_dict = {filter_dict.get(key, None): value for key, value in data.items() if
                          value or isinstance(value, (int, float))}
            query_dict = {key: value for key, value in query_dict.items() if key}
            # query_dict["is_deleted"] = False
            query_dict['is_application'] = False

            queryset = User.objects.filter(**query_dict).order_by("first_name")
            queryset = apply_date_time_range_filters(queryset, data)

            search_value = data.get("search")
            global_q = build_user_global_search_q(search_value) if search_value else None
            if global_q:
                queryset = queryset.filter(global_q).distinct()

            created_by_name = data.get("created_by_name")
            modified_by_name = data.get("modified_by_name")
            if created_by_name:
                user_ids = return_user_id_by_name(created_by_name)
                queryset = queryset.filter(created_by__in=user_ids)
            if modified_by_name:
                user_ids = return_user_id_by_name(modified_by_name)
                queryset = queryset.filter(modified_by__in=user_ids)
            if user_status == 0:
                queryset = queryset.filter(status=0)
            elif user_status == 1:
                queryset = queryset.filter(status=1)

            if application_id and not self.request.user.is_superuser:
                app_ids = UserRole.objects.filter(user=request.user).values_list("role__application_id", flat=True)
                if application_id in app_ids:
                    user_ids = UserRole.objects.filter(role__application_id=application_id).values_list("user_id",
                                                                                                        flat=True)
                    queryset = queryset.filter(id__in=user_ids)
                else:
                    queryset = queryset.filter(id=-1)
            if application_id and self.request.user.is_superuser:
                user_ids = UserRole.objects.filter(role__application_id=application_id).values_list("user_id",
                                                                                                    flat=True)
                queryset = queryset.filter(id__in=user_ids)

            total_is_active = User.objects.filter(status=True).count()
            total_inactive = User.objects.filter(is_deleted=True, status=False).count()

            order_by_dict = {
                "status": "status", "is_superuser": "is_superuser", "email": "email", "first_name": "first_name",
                "last_name": "last_name", "is_deleted": "is_deleted", "organisation_name": "organisation_name",
                "phone_number": "phone_number", 'country_code': 'country_code', "created_on": "created_on",
                "last_login": "last_login", "modified_by": "modified_by", "modified_on": "modified_on",
                "created_by": "created_by", "role_name": "role_user__role__role_name"
            }

            query_filter = order_by_dict.get(order_by, None)
            if order_type == "desc" and query_filter:
                query_filter = f"-{query_filter}"
            if query_filter:
                queryset = queryset.order_by(query_filter)

            if data.get("export"):
                serializer = self.serializer_class(queryset, many=True, context=self.request)
                return export_query_to_excel(data=serializer.data, module_name="USER_MANAGEMENT")

            # Create Paginator object with page_size objects per page
            paginator = Paginator(queryset, page_size)
            number_pages = paginator.num_pages
            if page > number_pages and page > 1:
                return Response({"message": "Page not found"}, status=status.HTTP_400_BAD_REQUEST)
            # Get the page object for the requested page number
            page_obj = paginator.get_page(page)
            serializer = self.serializer_class(page_obj, many=True, context=self.request)
            data = serializer.data

            return Response({"count": queryset.count(), "total_is_active": total_is_active, "total_inactive": total_inactive, "results": data}, status=status.HTTP_200_OK)
        except Exception as ee:
            return Response(str(ee), status=status.HTTP_400_BAD_REQUEST)


class UserDetailApi(RetrieveAPIView):
    """
    This view class is used to view an existing user
    """

    permission_classes = (CozentusPermission,)
    serializer_class = UserReadSerializer
    queryset = User.objects.all()


class UserShortInfoApi(RetrieveAPIView):
    """
    This view class is used to view an existing user for less info
    """
    vendor_booking_tool_object_permissions = {
        'GET': (permission_user_short_info,)
    }
    permission_classes = (CozentusPermission,)
    serializer_class = UserShortInfoSerializer
    queryset = User.objects.all()


class UserProfileApi(RetrieveAPIView):
    """
    This view class is used to view an existing user
    """

    permission_classes = (CozentusPermission,)
    serializer_class = UserProfileReadSerializer
    queryset = User.objects.all()

    def get_object(self):
        queryset = self.get_queryset()
        obj = get_object_or_404(queryset, email=self.request.user.email)
        return obj


class UserRegisterApi(CreateAPIView):
    serializer_class = UserRegisterSerializer
    queryset = User.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id)

class UserCreatePrivilegeApi(CreateAPIView):
    permission_classes = (CozentusPermission,)
    vendor_booking_tool_object_permissions = {"SUPER_USER": "New User Added!"}
    serializer_class = UserRoleSerializer
    queryset = User.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id)


class UserUpdatePrivilegeApi(UpdateAPIView):
    permission_classes = (CozentusPermission,)
    vendor_booking_tool_object_permissions = {"SUPER_USER": "User Access Updated!"}
    serializer_class = UserRoleSerializer
    queryset = User.objects.all()

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user.id, modified_on=datetime.now(timezone.utc))


class UserModifyApi(RetrieveUpdateDestroyAPIView):
    """
    User Modify api of specific user from super admin user by providing user id
    """
    vendor_booking_tool_object_permissions = {
        # 'GET': (permission_profile_details,),
        'PUT': (permission_user_detail_edit,),
        'PATCH': (permission_user_detail_edit,),
        'DELETE': (permission_user_detail_delete,)
    }
    permission_classes = (CozentusPermission,)
    serializer_class = UserEditSerializer
    queryset = User.objects.filter()

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user.id,
                        modified_on=datetime.now(timezone.utc))

    def perform_destroy(self, instance):
        instance.status = False
        instance.is_deleted = True
        instance.save()


class UserJsonDataAPI(GenericAPIView):
    permission_classes = (CozentusPermission,)
    serializer_class = UserSerializers

    @staticmethod
    def get(request):
        queryset = User.objects.values('id', 'first_name', 'last_name')
        user_dict = {user['id']: f"{user['first_name']} {user['last_name']}".strip() for user in queryset}
        return Response({"count": len(user_dict), "results": user_dict}, status=status.HTTP_200_OK)


class UserUpdateIsSuperUserApi(UpdateAPIView):
    permission_classes = (CozentusPermission,)
    vendor_booking_tool_object_permissions = {"SUPER_USER": "Super User Status Updated!"}
    serializer_class = UpdateSuperUserSerializer
    queryset = User.objects.all()

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user.id, modified_on=datetime.now(timezone.utc))


class UserProfileAccessApi(GenericAPIView):
    permission_classes = (CozentusPermission,)
    serializer_class = UserSerializers

    def get(self, request, user_id):
        try:
            # Fetch the user profile
            profile = User.objects.get(id=user_id)
            if not profile:
                return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

            # Fetch application and role ids
            user_roles = UserRole.objects.filter(user=profile)
            role_ids = user_roles.values_list("role__id", flat=True)



            # Prepare response data
            data = []

            return Response(data, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)