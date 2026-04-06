from django.db import models, transaction
from rest_framework import serializers

from master_data_management.models import PortOfLoading


class PortOfLoadingReadSerializer(serializers.ModelSerializer):

    class Meta:
        model = PortOfLoading
        fields = '__all__'
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
                if PortOfLoading.objects.filter(code=code).exists():
                    raise serializers.ValidationError('Port with this code already exists! ')
                if PortOfLoading.objects.filter(unlocode=unlocode).exists():
                    raise serializers.ValidationError('Port with this unlocode already exists! ')
                if PortOfLoading.objects.filter(supplyx_code=supplyx_code).exists():
                    raise serializers.ValidationError('Port with this supplyx_code already exists! ')





        except Exception as e:
            raise serializers.ValidationError(str(e))

        return data

class PortOfLoadingFilterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50,required=False,allow_blank=True,allow_null=True)
    code = serializers.CharField(max_length=50,required=False,allow_blank=True,allow_null=True)
    unlocode = serializers.CharField(max_length=50,required=False,allow_blank=True,allow_null=True)
    country = serializers.CharField(max_length=50,required=False,allow_blank=True,allow_null=True)
    timezone = serializers.CharField(max_length=50,required=False,allow_blank=True,allow_null=True)
    latitude = serializers.DecimalField(max_digits=9,decimal_places=6,required=False,allow_null=True)
    longitude = serializers.DecimalField(max_digits=9,decimal_places=6,required=False,allow_null=True)
    supplyx_code = serializers.CharField(max_length=50,required=False,allow_blank=True,allow_null=True)
    is_active = serializers.BooleanField(required=False,default=True)
    address = serializers.CharField(required=False,allow_blank=True,allow_null=True)
    modified_by = serializers.CharField(required=False,allow_blank=True,allow_null=True)
    created_by = serializers.CharField(required=False,allow_blank=True,allow_null=True)

    order_by = serializers.CharField(max_length=100,required=False,allow_blank=True,allow_null=True)
    order_type = serializers.ChoiceField(choices=["asc","desc"],required=False,allow_blank=True,allow_null=True)
    page = serializers.IntegerField(default=1,allow_null=True)
    page_size = serializers.IntegerField(default=50,allow_null=True)




