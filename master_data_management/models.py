from django.db import models
from vendor_booking_tool.utility import BaseUserModel
from shipement_management.utility import TransportModeEnum
from user_management.models import User
from acl.models import Role


# Create your models here.

class PortOfLoading(BaseUserModel):
    name = models.CharField(max_length=50, blank=True, null=True)
    code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    country = models.CharField(max_length=20, blank=True, null=True)
    unlocode = models.CharField(max_length=50, unique=True)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    supplyx_code= models.CharField(max_length=50, null=True, blank=True)


    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = "Port of Loading"
        verbose_name_plural = "Ports of Loading"
        ordering = ['name']
        db_table = "PORT_OF_LOADING"

class PortOfDestination(BaseUserModel):
    name = models.CharField(max_length=50, blank=True, null=True)
    code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=20, blank=True, null=True)
    unlocode = models.CharField(max_length=50)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    supplyx_code = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        verbose_name = "Port of Destination"
        verbose_name_plural = "Ports of Destination"
        ordering = ['name']
        db_table = "PORT_OF_DESTINATION"

class Company(BaseUserModel):
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50, blank=True, null=True)
    company_type = models.PositiveIntegerField()
    country = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    parent_company = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    optionals = models.JSONField(default=list, blank=True)
    supplyx_code = models.CharField(max_length=250, null=True, blank=True)
    contact_person = models.CharField(max_length=100)
    address = models.TextField(null=True, blank=True)


    class Meta:
        db_table = "COMPANY"
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ['name']

    def __str__(self):
        return self.name

class CustomerField(BaseUserModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="custom_fields")
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "CUSTOMER_FIELD"
        verbose_name = "Customer Field"
        verbose_name_plural = "Customer Fields"

    def __str__(self):
        return self.name

class Carrier(BaseUserModel):
    name = models.CharField(max_length=100)
    carrier_code = models.CharField(max_length=50)
    transportation_mode = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    description = models.TextField(null=True, blank=True)
    supplyx_code = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = "CARRIER"
        verbose_name = "Carrier"
        verbose_name_plural = "Carriers"
        ordering = ['name']

    def __str__(self):
        return self.name

class UserCompany(BaseUserModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_companies")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="company_users")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_on']
        db_table = "USER_COMPANY"
        verbose_name_plural = "User Companies"
        constraints = [
            models.UniqueConstraint(fields=['user', 'company'], name='unique_user_company')
        ]

    def __str__(self):
        return f"{self.user.first_name} - > {self.company.name}"

class CompanyCustomer(BaseUserModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="company_customers")
    customer_company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="customer_companies")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "COMPANY_CUSTOMER"
        ordering = ['created_on']
        verbose_name_plural = "Company Customers"

class TransportMode(BaseUserModel):
    """
    Master table to store different transport modes.
    Example: Air, Sea, Road, Rail.
    """
    mode_name = models.CharField(max_length=100)
    description = models.CharField(max_length=250, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "TRANSPORT_MODE"
        ordering = ['-created_on']

class ShipmentType(BaseUserModel):
    """
    Master table to store types of shipments.
    Example: FCL, LCL, Courier, Express.
    """
    mode = models.ForeignKey(
        TransportMode,
        on_delete=models.CASCADE,
        related_name="shipment_types"
    )
    shipment_type_name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "SHIPMENT_TYPE"
        verbose_name = "Shipment Type"
        verbose_name_plural = "Shipment Types"
        ordering = ['shipment_type_name']

class EquipmentType(BaseUserModel):
    """
    Master table to store types of transport equipment.
    Example: 20FT Container, 40FT Container, Flat Rack, Reefer.
    """
    mode = models.ForeignKey(
        TransportMode,
        on_delete=models.CASCADE,
        related_name="equipment_types"
    )
    equipment_name = models.CharField(max_length=50)
    equipment_category = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    iso_code = models.CharField(max_length=50, blank=True, null=True)
    supplyx_code = models.CharField(max_length=50, blank=True, null=True)
    equipment_size = models.CharField(max_length=50, blank=True, null=True)
    equipment_height = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "EQUIPMENT_TYPE"
        verbose_name = "Equipment Type"
        verbose_name_plural = "Equipment Types"
        ordering = ['equipment_name']

class CompanyType(BaseUserModel):
    """
    Master table to store types of logistics companies.
    Example: Vendor, Origin Agent, Destination Agent, Customer, Supplier.
    """
    company_type_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "COMPANY_TYPE"
        verbose_name = "Company Type"
        verbose_name_plural = "Company Types"
        ordering = ['company_type_name']

class Incoterm(BaseUserModel):
    """
    Master table to store INCOTERM (International Commercial Terms) data.
    Example: EXW, FOB, FCA, DAP, etc.
    """
    incoterm_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "INCOTERM"
        verbose_name = "Incoterm"
        verbose_name_plural = "Incoterms"
        ordering = ['incoterm_name']

class Supplier(BaseUserModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="suppliers")
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50)
    country = models.CharField(max_length=50)
    email = models.EmailField(max_length=30, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    description = models.TextField(max_length=250, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table  = "SUPPLIER"
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=["company", "code"], name="unique_supplier_per_company")
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

class StatusTransition(BaseUserModel):
    status_from = models.PositiveIntegerField(db_column="STATUS_FROM")
    status_to = models.PositiveIntegerField(db_column="STATUS_TO")
    is_active = models.BooleanField(default=True, db_column="IS_ACTIVE")

    class Meta:
        db_table = "STATUS_TRANSITION"

class StatusTransitionRole(BaseUserModel):
    transition = models.ForeignKey(StatusTransition, on_delete=models.CASCADE, related_name="allowed_roles", db_column="TRANSITION_ID")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="status_transitions", db_column="ROLE_ID")

    class Meta:
        db_table = "STATUS_TRANSITION_ROLE"

class CompanyPOL(BaseUserModel):
    company = models.ForeignKey(Company, on_delete=models.DO_NOTHING, db_column="company_id")
    pol = models.ForeignKey(PortOfLoading, on_delete=models.DO_NOTHING, db_column="pol_id")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "COMPANY_POL"
        verbose_name = "Company_POL"
        verbose_name_plural = "COMPANY_POL_MAPPING"


class CompanyPOD(BaseUserModel):
    company = models.ForeignKey(Company, on_delete=models.DO_NOTHING, db_column="company_id")
    pod = models.ForeignKey(PortOfDestination, on_delete=models.DO_NOTHING, db_column="pod_id")
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "COMPANY_POD"
        verbose_name = "Company_POD"
        verbose_name_plural = "COMPANY_POD_MAPPING"