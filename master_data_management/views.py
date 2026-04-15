from datetime import timezone, datetime
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import render
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView, GenericAPIView, ListAPIView

from acl.privilege import CozentusPermission
from master_data_management.models import PortOfLoading
from .serializers import PortOfLoadingReadSerializer, PortOfLoadingFilterSerializer, CarrierFilterSerializer, CompanyCreateSerializer
from user_management.utility import return_user_id_by_name
from vendor_booking_tool.utility import apply_date_time_range_filters
from master_data_management.models import PortOfDestination

from .models import Carrier, Company
from .serializers import PortOfDestinationReadSerializer, PortOfDestinationFilterSerializer, CarrierCreateSerializer, \
    CarrierReadSerializer, CarrierModifySerializer


# --------- Port of Loading  --------------------

class PortOfLoadingCreateApiView(CreateAPIView):
    permission_classes = (CozentusPermission,)

    serializer_class = PortOfLoadingReadSerializer
    queryset = PortOfLoading.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id, )


class PortOfLoadingModifyApiView(RetrieveUpdateDestroyAPIView):
    permission_classes = (CozentusPermission,)
    serializer_class = PortOfLoadingReadSerializer
    queryset = PortOfLoading.objects.all()

    def perform_update(self, serializer):
        serializer.save(
            modified_by=self.request.user.id,
            modified_on=datetime.now(timezone.utc)
        )

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class PortOfLoadingFilterApiView(GenericAPIView):
    permission_classes = (CozentusPermission,)
    serializer_class = PortOfLoadingFilterSerializer

    @extend_schema(request=PortOfLoadingFilterSerializer)
    def post(self, request):
        serializer = PortOfLoadingFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            page_size = data.get("page_size", 50) if data.get("page_size") else 50
            page = data.get("page", 1) if data.get("page") else 1
            if page < 1 and page_size < 1:
                return Response({"message": "Page and Page Size should be positive interger"},
                                status=status.HTTP_400_BAD_REQUEST)
            order_by = data.get("order_by", None)
            order_type = request.data.get("order_type")

            filter_dict = {
                'name': 'name__icontains',
                'code': 'code',
                'country': 'country__icontains',
                'unlocode': 'unlocode',
                'timezone': 'timezone__icontains',
                'latitude': 'latitude',
                'longitude': 'longitude',
                'address': 'address',
                'description': 'description',
                'is_active': 'is_active',
                'supplyx_code': 'supplyx_code',
                'status': 'status',
            }

            query_dict = {filter_dict.get(key, None): value for key, value in data.items()
                          if key in filter_dict and value is not None}
            query_dict = {key: value for key, value in query_dict.items() if key}

            queryset = PortOfLoading.objects.filter(**query_dict).order_by("name")

            search_value = data.get("search")

            # queryset = apply_date_time_range_filters(queryset, data)

            created_by_name = data.get("created_by_name")
            modified_by_name = data.get("modified_by_name")

            if created_by_name:
                user_ids = return_user_id_by_name(created_by_name)
                queryset = queryset.filter(created_by=user_ids)
            if modified_by_name:
                user_ids = return_user_id_by_name(modified_by_name)
                queryset = queryset.filter(created_by=user_ids)

            total_count = PortOfLoading.objects.aggregate(
                total_active=Count('id', filter=Q(is_active=True)),
                total_inactive=Count('id', filter=Q(is_active=False))
            )

            total_is_active = total_count["total_active"] or 0
            total_inactive = total_count["total_inactive"] or 0

            # order mapping
            order_by_dict = {
                'name': 'name',
                'code': 'code',
                'country': 'country',
                'unlocode': 'unlocode',
                'timezone': 'timezone',
                'latitude': 'latitude',
                'longitude': 'longitude',
                'address': 'address',
                'description': 'description',
                'is_active': 'is_active',
                'supplyx_code': 'supplyx_code',
            }

            query_filter = order_by_dict.get(order_by, None)
            if order_type == "desc" and query_filter:
                query_filter = f"-{query_filter}"
            if query_filter:
                queryset = queryset.ordered(query_filter)

            # create paginator
            paginator = Paginator(queryset, page_size)
            number_pages = paginator.num_pages

            if page > number_pages and page > 1:
                return Response({'message': "Page not found "}, status=status.HTTP_400_BAD_REQUEST)

            page_obj = paginator.get_page(page)
            serializer = PortOfLoadingReadSerializer(page_obj, many=True, context=self.request)
            data = serializer.data
            return Response({
                'count': queryset.count(),
                'total_is_active': total_is_active,
                'total_inactive': total_inactive,
                'results': data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# --------- Port of Destiation --------------------

class PortOfPortOfDestinationCreateApiView(CreateAPIView):
    permission_classes = (CozentusPermission,)

    serializer_class = PortOfDestinationReadSerializer
    queryset = PortOfDestination.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id)


class PortOfDestinationModifyApiView(RetrieveUpdateDestroyAPIView):
    permission_classes = (CozentusPermission,)
    serializer_class = PortOfDestinationReadSerializer

    def perform_update(self, serializer):
        serializer.save(
            modified_by=self.request.user.id,
            modified_on=datetime.now(timezone.utc)
        )

    def perform_destroy(self, instance):
        print('called ')
        instance.is_active = False
        instance.save()


class PortOfDestiationFilterApiView(GenericAPIView):
    permission_classes = (CozentusPermission,)
    serializer_class = PortOfDestinationFilterSerializer

    @extend_schema(request=PortOfDestinationFilterSerializer)
    def post(self, request):
        serializer = PortOfDestinationFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            page_size = data.get("page_size", 50) if data.get("page_size") else 50
            page = data.get("page", 1) if data.get("page") else 1
            if page < 1 and page_size < 1:
                return Response({"message": "Page and Page Size should be positive interger"},
                                status=status.HTTP_400_BAD_REQUEST)
            order_by = data.get("order_by", None)
            order_type = request.data.get("order_type")

            filter_dict = {
                'name': 'name__icontains',
                'code': 'code',
                'country': 'country__icontains',
                'unlocode': 'unlocode',
                'timezone': 'timezone__icontains',
                'latitude': 'latitude',
                'longitude': 'longitude',
                'address': 'address',
                'description': 'description',
                'is_active': 'is_active',
                'supplyx_code': 'supplyx_code',
                'status': 'status',
            }

            query_dict = {filter_dict.get(key, None): value for key, value in data.items()
                          if key in filter_dict and value is not None}
            query_dict = {key: value for key, value in query_dict.items() if key}

            queryset = PortOfDestination.objects.filter(**query_dict).order_by("name")

            search_value = data.get("search")

            # queryset = apply_date_time_range_filters(queryset, data)

            created_by_name = data.get("created_by_name")
            modified_by_name = data.get("modified_by_name")

            if created_by_name:
                user_ids = return_user_id_by_name(created_by_name)
                queryset = queryset.filter(created_by=user_ids)
            if modified_by_name:
                user_ids = return_user_id_by_name(modified_by_name)
                queryset = queryset.filter(created_by=user_ids)

            total_count = PortOfDestination.objects.aggregate(
                total_active=Count('id', filter=Q(is_active=True)),
                total_inactive=Count('id', filter=Q(is_active=False))
            )

            total_is_active = total_count["total_active"] or 0
            total_inactive = total_count["total_inactive"] or 0

            # order mapping
            order_by_dict = {
                'name': 'name',
                'code': 'code',
                'country': 'country',
                'unlocode': 'unlocode',
                'timezone': 'timezone',
                'latitude': 'latitude',
                'longitude': 'longitude',
                'address': 'address',
                'description': 'description',
                'is_active': 'is_active',
                'supplyx_code': 'supplyx_code',
            }

            query_filter = order_by_dict.get(order_by, None)
            if order_type == "desc" and query_filter:
                query_filter = f"-{query_filter}"
            if query_filter:
                queryset = queryset.ordered(query_filter)

            # create paginator
            paginator = Paginator(queryset, page_size)
            number_pages = paginator.num_pages

            if page > number_pages and page > 1:
                return Response({'message': "Page not found "}, status=status.HTTP_400_BAD_REQUEST)

            page_obj = paginator.get_page(page)
            serializer = PortOfDestinationReadSerializer(page_obj, many=True, context=self.request)
            data = serializer.data
            return Response({
                'count': queryset.count(),
                'total_is_active': total_is_active,
                'total_inactive': total_inactive,
                'results': data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ---------------- Carrier ------------------

class CarrierCreateApiView(CreateAPIView):
    permission_classes = (CozentusPermission,)
    serializer_class = CarrierCreateSerializer
    queryset = Carrier.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id)


class CarrierModifyApiView(RetrieveUpdateDestroyAPIView):
    permission_classes = (CozentusPermission,)
    queryset = Carrier.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CarrierReadSerializer
        return CarrierModifySerializer

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user.id,
                        modified_on = datetime.now())

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()


class CarrierFilterApiView(ListAPIView):
    permission_classes = (CozentusPermission,)
    serializer_class = CarrierFilterSerializer

    @extend_schema(request=CarrierFilterSerializer)
    def post(self, request):
        serializer = CarrierFilterSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

        try:
            page_size = data.get("page_size", 50) if data.get("page_size") else 50
            page = data.get("page", 1) if data.get("page") else 1
            if page < 1 and page_size < 1:
                return Response({"message": "Page and Page Size should be positive interger"},
                                status=status.HTTP_400_BAD_REQUEST)
            order_by = data.get("order_by", None)
            order_type = request.data.get("order_type")

            filter_dict = {
                'name': 'name__icontains',
                'carrier_code': 'carrier_code',
                'transportation_mode': 'transportation_mode',
                'is_active': 'is_active',
                'supplyx_code': 'supplyx_code',
                'description': 'description',
            }

            query_dict = {filter_dict.get(key, None): value for key, value in data.items()
                          if key in filter_dict and value is not None}
            query_dict = {key: value for key, value in query_dict.items() if key}

            queryset = Carrier.objects.filter(**query_dict).order_by("name")

            search_value = data.get("search")

            queryset = apply_date_time_range_filters(queryset, data)

            created_by_name = data.get("created_by_name")
            modified_by_name = data.get("modified_by_name")

            if created_by_name:
                user_ids = return_user_id_by_name(created_by_name)
                queryset = queryset.filter(created_by=user_ids)
            if modified_by_name:
                user_ids = return_user_id_by_name(modified_by_name)
                queryset = queryset.filter(created_by=user_ids)

            total_count = Carrier.objects.aggregate(
                total_active=Count('id', filter=Q(is_active=True)),
                total_inactive=Count('id', filter=Q(is_active=False))
            )

            total_is_active = total_count["total_active"] or 0
            total_inactive = total_count["total_inactive"] or 0

            # order mapping
            order_by_dict = {
                'name': 'name__icontains',
                'carrier_code': 'carrier_code',
                'transportation_mode': 'transportation_mode',
                'is_active': 'is_active',
                'supplyx_code': 'supplyx_code',
                'description': 'description',
            }

            query_filter = order_by_dict.get(order_by, None)
            if order_type == "desc" and query_filter:
                query_filter = f"-{query_filter}"
            if query_filter:
                queryset = queryset.ordered(query_filter)

            # create paginator
            paginator = Paginator(queryset, page_size)
            number_pages = paginator.num_pages

            if page > number_pages and page > 1:
                return Response({'message': "Page not found "}, status=status.HTTP_400_BAD_REQUEST)

            page_obj = paginator.get_page(page)
            serializer = CarrierReadSerializer(page_obj, many=True, context=self.request)
            data = serializer.data
            return Response({
                'count': queryset.count(),
                'total_is_active': total_is_active,
                'total_inactive': total_inactive,
                'results': data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


#         --------------------- Company --------------------------------

class CreateCompanyApiView(CreateAPIView):
    permission_classes = (CozentusPermission,)

    serializer_class = CompanyCreateSerializer
    queryset = Company.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id)




