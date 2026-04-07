import re

from django.db import models, transaction
from rest_framework import serializers

from master_data_management.models import PortOfLoading

from vendor_booking_tool.utility import validate_decimal_coordinate

from master_data_management.models import PortOfDestination


class PortOfLoadingReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortOfLoading
        fields = ('id', 'name', 'code', 'country', 'unlocode', 'timezone', 'is_active', "latitude", "longitude",
                  'address', 'description', 'created_on', 'created_by', 'supplyx_code')
        read_only_fields = (

            'created_on',
            'created_by',
            'modified_on',
            'modified_by',
        )

    def validate(self, data):
        code = data.get('code')
        unlocode = data.get('unlocode')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        supplyx_code = data.get('supplyx_code')
        name = data.get('name')
        try:
            with transaction.atomic():
                if name:
                    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
                        raise serializers.ValidationError('Port name contains only alphabets and punctuation ')
                    if len(name) > 50:
                        raise serializers.ValidationError('Port name contains more than 50 characters! ')
                if PortOfLoading.objects.filter(code=code).exists():
                    raise serializers.ValidationError('Port with this code already exists! ')
                if 'unlocode' in data:
                    if not unlocode:
                        raise serializers.ValidationError({"unlocode": "unlocode is required"})
                    if not re.match(r"^[a-zA-Z0-9_-]{5}$", unlocode):
                        raise serializers.ValidationError({"unlocode": "Invalid format"})

                if latitude is not None:
                    validate_decimal_coordinate(latitude, "latitude", -90, 90)

                if longitude is not None:
                    validate_decimal_coordinate(longitude, "longitude", -180, 180)

                if PortOfLoading.objects.filter(supplyx_code=supplyx_code).exists():
                    raise serializers.ValidationError('Port with this supplyx_code already exists! ')
        except Exception as e:
            raise serializers.ValidationError(str(e))

        return data


class PortOfLoadingFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    name = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    code = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    country = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    timezone = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    unlocode = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    address = serializers.CharField(required=False, max_length=250, allow_null=True, allow_blank=True)
    description = serializers.CharField(required=False, max_length=250, allow_null=True, allow_blank=True)
    is_active = serializers.BooleanField(required=False, allow_null=True)
    created_by = serializers.IntegerField(required=False, allow_null=True)
    modified_by = serializers.IntegerField(required=False, allow_null=True)

    order_by = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True, write_only=True)
    order_type = serializers.ChoiceField(choices=["asc", "desc"], required=False, allow_blank=True, allow_null=True)
    page = serializers.IntegerField(default=1, allow_null=True)
    page_size = serializers.IntegerField(default=50, allow_null=True)

# --------------------------------------------------------------------------

class PortOfDestinationReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortOfDestination
        fields =('id','name','code','country','unlocode','timezone','latitude','longitude','supplyx_code','address','is_active','description',)


        def validate(self, data):
            try:
                with transaction.atomic():
                    name = data.get('name')
                    code = data.get('code')
                    latitude = data.get('latitude')
                    longitude = data.get('longitude')
                    is_active = data.get('is_active')
                    supplyx_code = data.get('supplyx_code')
                    unlocode = data.get('unlocode')

                    if name:
                        if not re.match(r"^[a-zA-Z0-9_-]{3}$", name):
                            raise serializers.ValidationError('Port name contains only alphabets and punctuation ')
                        if len(name) > 50:
                            raise serializers.ValidationError(f'{name} shold be less than 50 characters ')

                    if code:
                        if PortOfLoading.objects.filter(code=code).exists():
                            raise serializers.ValidationError('Port with this code already exists! ')

                    if latitude is not None:
                        validate_decimal_coordinate(latitude, "latitude", -90, 90)
                    if longitude is not None:
                        validate_decimal_coordinate(longitude, "longitude", -180, 180)

                    if supplyx_code:
                        if PortOfDestination.objects.filter(supplyx_code=supplyx_code).exists():
                            raise serializers.ValidationError('Port  with this supplyx_code already exists! ')

                    if 'unlocode' in data:
                        if not unlocode:
                            raise serializers.ValidationError({"unlocode": "unlocode is required"})
                        if not re.match(r"^[a-zA-Z0-9_-]{5}$", unlocode):
                            raise serializers.ValidationError({"unlocode": "Invalid format"})

            except Exception as e:
                raise serializers.ValidationError(str(e))

class PortOfDestinationFilterSerializer(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    name = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    code = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    country = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    timezone = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    unlocode = serializers.CharField(max_length=50, required=False, allow_null=True, allow_blank=True)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False, allow_null=True)
    address = serializers.CharField(required=False, max_length=250, allow_null=True, allow_blank=True)
    description = serializers.CharField(required=False, max_length=250, allow_null=True, allow_blank=True)
    is_active = serializers.BooleanField(required=False, allow_null=True)
    created_by_name = serializers.CharField(required=False)
    modified_by_name = serializers.CharField(required=False)

    order_by = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True, write_only=True)
    order_type = serializers.ChoiceField(choices=["asc", "desc"], required=False, allow_blank=True, allow_null=True)
    page = serializers.IntegerField(default=1, allow_null=True)
    page_size = serializers.IntegerField(default=50, allow_null=True)














