from django.db import models
from vendor_booking_tool.utility import BaseUserModel
from master_data_management.models import Company, CustomerField, PortOfLoading, PortOfDestination, EquipmentType, \
                                            ShipmentType, Incoterm, Carrier
from user_management.models import User
from .utility import ShipmentStatusEnum, TransportModeEnum, ServiceTypeEnum


# Create your models here.

class File(BaseUserModel):
    original_file_name = models.CharField(max_length=300)
    new_file_name = models.CharField(max_length=300, null=True, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    container_name = models.CharField(max_length=100)
    storage_type = models.CharField(max_length=200, null=True, blank=True)
    file_path = models.CharField(max_length=300, null=True, blank=True)
    output_file_name = models.CharField(max_length=300, null=True, blank=True)
    objects = models.Manager()

    class Meta:
        ordering = ['-id']
        db_table = 'FILE'


class InputFile(BaseUserModel):
    file_id = models.ForeignKey(File, on_delete=models.DO_NOTHING, null=True, db_column="file_id",
                                related_name="in_file_id")
    shipment = models.CharField(max_length=100, null=True, blank=True)
    customer = models.CharField(max_length=100, null=True, blank=True)
    supplier = models.CharField(max_length=100, null=True, blank=True)
    volume = models.FloatField(null=True, blank=True)
    quantity = models.FloatField(null=True, blank=True)
    pol = models.CharField(max_length=100, null=True, blank=True)
    pod = models.CharField(max_length=100, null=True, blank=True)
    date = models.DateTimeField(null=True, blank=True)
    priority_index = models.CharField(max_length=100, null=True, blank=True)
    bucket = models.CharField(max_length=100, null=True, blank=True)
    container = models.CharField(max_length=100, null=True, blank=True)

    objects = models.Manager()

    class Meta:
        ordering = ['-id']
        db_table = 'INPUT_FILE'


class OutputFile(BaseUserModel):
    file_id = models.ForeignKey(File, on_delete=models.DO_NOTHING, null=True, db_column="file_id",
                                related_name="out_file_id")
    container_ref = models.CharField(max_length=250)
    container_type = models.CharField(max_length=50)
    shipment = models.CharField(max_length=100, null=True, blank=True)
    customer = models.CharField(max_length=100, null=True, blank=True)
    supplier = models.CharField(max_length=100, null=True, blank=True)
    cbm = models.FloatField(null=True, blank=True)
    total_cbm = models.FloatField(null=True, blank=True)
    qty = models.FloatField(null=True, blank=True)
    total_qty = models.FloatField(null=True, blank=True)
    pol = models.CharField(max_length=100, null=True, blank=True)
    pod = models.CharField(max_length=100, null=True, blank=True)
    min_threshold = models.PositiveIntegerField(null=True, blank=True)
    max_threshold = models.PositiveIntegerField(null=True, blank=True)

    objects = models.Manager()

    class Meta:
        ordering = ['-id']
        db_table = "OUTPUT_FILE"


class ShipmentOrder(BaseUserModel):
    """
    Represents a shipment booking containing cargo, routing, and logistics details.
    """

    vendor_booking_number = models.CharField(
        max_length=20,
        unique=True,
        help_text="System-generated booking number (e.g., VBK250911001)"
    )

    vendor_booking_status = models.PositiveIntegerField(
        help_text="Order status: Draft, Confirmed, Booked, Cancelled or Shipped",
        null=True,
        blank=True
    )

    shipper = models.CharField(max_length=255, null=True, blank=True)
    consignee = models.CharField(max_length=255, null=True, blank=True)

    transportation_mode = models.PositiveIntegerField(null=True, blank=True)
    cargo_readiness_date = models.DateTimeField(null=True, blank=True)
    service_type = models.PositiveIntegerField(null=True, blank=True)

    hs_code = models.CharField(max_length=50, null=True, blank=True)
    cargo_description = models.TextField(null=True, blank=True)
    marks_and_numbers = models.CharField(max_length=255, null=True, blank=True)
    cargo_type = models.PositiveIntegerField(null=True, blank=True)
    dangerous_goods_notes = models.TextField(null=True, blank=True)

    place_of_receipt = models.CharField(max_length=255, null=True, blank=True)
    place_of_delivery = models.CharField(max_length=255, null=True, blank=True)

    carrier = models.ForeignKey(Carrier,on_delete=models.CASCADE,related_name="shipments_carrier", null=True, blank=True)
    carrier_booking_number = models.CharField(max_length=100, null=True, blank=True)

    customer = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        related_name="shipment_orders",
        null=True,
        blank=True,
    )

    notify_party_1 = models.CharField(max_length=255, null=True, blank=True)
    notify_party_2 = models.CharField(max_length=255, null=True, blank=True)

    volume_booked = models.FloatField(null=True, blank=True)
    volume_actual = models.FloatField(null=True, blank=True)
    weight_booked = models.FloatField(null=True, blank=True)
    weight_actual = models.FloatField(null=True, blank=True)
    quantity_booked = models.FloatField(null=True, blank=True)
    quantity_actual = models.FloatField(null=True, blank=True)

    incoterm = models.PositiveIntegerField(null=True, blank=True)
    payment_terms = models.PositiveIntegerField(null=True, blank=True)

    customer_reference = models.CharField(max_length=100, null=True, blank=True)
    vendor_reference = models.CharField(max_length=100, null=True, blank=True)
    agent_reference = models.CharField(max_length=100, null=True, blank=True)

    pol = models.ForeignKey(
        PortOfLoading,
        on_delete=models.SET_NULL,
        related_name="shipment_orders_pol",
        null=True,
        blank=True
    )
    pod = models.ForeignKey(
        PortOfDestination,
        on_delete=models.SET_NULL,
        related_name="shipment_orders_pod",
        null=True,
        blank=True
    )

    pickup_address = models.TextField(null=True, blank=True)


    shipment_type = models.ForeignKey(
        ShipmentType,
        on_delete=models.SET_NULL,
        related_name="shipment_orders_type",
        null=True,
        blank=True
    )

    vendor = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="shipment_orders_vendor",
        null=True,
        blank=True
    )

    origin_agent = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="shipment_orders_origin_agent",
        null=True,
        blank=True
    )

    destination_agent = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="shipment_orders_destination_agent",
        null=True,
        blank=True
    )

    equipment_count = models.IntegerField(null=True)
    equipment_types = models.JSONField(default=list, null=True, blank=True)
    equipment_no = models.JSONField(default=list,null=True, blank=True)
    vessel_name = models.CharField(max_length=100, null=True, blank=True)
    carrier_service_contract = models.CharField(max_length=100, null=True, blank=True)
    etd = models.DateTimeField(null=True, blank=True)
    eta = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)


    class Meta:
        db_table = "SHIPMENT_ORDERS"
        ordering = ["vendor_booking_number"]
        verbose_name_plural = "Shipment Orders"

    def __str__(self):
        return f"{self.vendor_booking_number} - {self.shipper or ''} → {self.consignee or ''}"

class ShipmentFieldValue(BaseUserModel):
    shipment_order = models.ForeignKey(ShipmentOrder, on_delete=models.CASCADE, related_name="custom_field_values", db_index=True)
    field = models.ForeignKey(CustomerField, on_delete=models.CASCADE, db_index=True)
    value = models.TextField()

    class Meta:
        db_table = "shipment_field_value"
        verbose_name = "Shipment Field Value"
        verbose_name_plural = "Shipment Field Values"

    def __str__(self):
        return f"{self.field.name}: {self.value}"