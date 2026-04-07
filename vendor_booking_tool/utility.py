import datetime
import random
from datetime import timedelta
from decimal import Decimal

from django.db import models
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination


def get_random_string(length=12, allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    """
    Return a  generated random string.
    """

    return ''.join(random.choice(allowed_chars) for _ in range(length))


class CustomPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 10000


def apply_date_time_range_filters(queryset, data, module_id=0):
    date_filters = {}
    summary_keys = ["due_date__gte", "received_on__gte", "invoice_date__gte", "due_date__lte", "received_on__lte",
                    "invoice_date__lte"]

    # Collect start and end date filters
    for key, value in data.items():
        if value and (key.endswith("_start_date") or key.endswith("_end_date")):
            filter_key = key.replace("_start_date", "__gte").replace("_end_date", "__lte")
            date_value = datetime.fromisoformat(value.replace("Z", "+00:00"))

            if filter_key.endswith("__lte"):
                date_value += timedelta(hours=23, minutes=59, seconds=59)
            if filter_key in summary_keys:
                filter_key = f'doc_details__{filter_key}'
            date_filters[filter_key] = date_value

    if date_filters:
        queryset = queryset.filter(**date_filters)

    return queryset


class BaseUserModel(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.PositiveIntegerField(null=True)
    modified_on = models.DateTimeField(null=True, blank=True)
    modified_by = models.PositiveIntegerField(null=True)

    objects = models.Manager()

    class Meta:
        abstract = True


def validate_decimal_coordinate(value,field_name:str , min_value:float, max_value:float):
    if value is None:
        return

    try:
        dec_value = Decimal(value)

        if dec_value < Decimal(min_value) and dec_value > Decimal(max_value):
            raise serializers.ValidationError(f"Decimal value {value} should be between {min_value} and {max_value} ")

    except (ValueError, TypeError):
        raise serializers.ValidationError(f"Decimal value {value} should be a decimal number ")