import dateutil.parser
import logging
from datetime import datetime, timezone, timedelta
import re

from django.utils import timezone as utils_timezone
from django.db.models import Q

from enum import Enum

DATE_FOLDER_FORMAT = "%Y/%m/%d"

DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%y/%m/%d",
    "%y-%m-%d",
    "%y\\%m\\%d",
    "%Y/%m",
    "%m-%d-%Y",
    "%m/%d/%Y",
]

def parse_search_date(value: str):
    """
    Try to parse date from multiple formats.
    Returns date or None.
    """
    if not isinstance(value, str):
        return None

    value = value.strip()

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None

def parse_year_month(value: str):
    """
    Parses:
    - YYYY/MM or YYYY-MM
    - MM/YYYY or MM-YYYY
    - MM/YY or MM-YY

    Returns (year, month) or None
    """
    value = value.strip()

    # YYYY/MM or YYYY-MM
    match_ym = re.match(r"^(\d{4})[\/\-](\d{1,2})$", value)
    if match_ym:
        year, month = int(match_ym.group(1)), int(match_ym.group(2))
        if 1 <= month <= 12:
            return year, month
        return None

    # MM/YYYY or MM-YYYY
    match_my4 = re.match(r"^(\d{1,2})[\/\-](\d{4})$", value)
    if match_my4:
        month, year = int(match_my4.group(1)), int(match_my4.group(2))
        if 1 <= month <= 12:
            return year, month
        return None

    # MM/YY or MM-YY
    match_my2 = re.match(r"^(\d{1,2})[\/\-](\d{2})$", value)
    if match_my2:
        month, year = int(match_my2.group(1)), int(match_my2.group(2))
        if 1 <= month <= 12:
            return 2000 + year, month
        return None

    return None

def parse_day_month(value: str):
    """
    Parses:
    - DD/MM
    - DD-MM

    Returns (month, day) or None
    """
    value = value.strip()

    match = re.match(r"^(\d{1,2})[\/\-](\d{1,2})$", value)
    if not match:
        return None

    day, month = int(match.group(1)), int(match.group(2))

    if 1 <= day <= 31 and 1 <= month <= 12:
        return month, day

    return None

def get_custom_folder_path(document_type_id, is_temporary, data_dict: dict, application_name,
                           le_id=None, document_type_name=""):
    folder_path = []

    # Append the current date in YYYY/MM/DD format
    current_date = datetime.now().strftime(DATE_FOLDER_FORMAT)

    folder_path.append(current_date)

    return "/".join(folder_path)


class BaseEnum(Enum):
    def __init__(self, code, description):
        self.CODE = code
        self.DESCRIPTION = description

    @classmethod
    def get_module_id_by_name(cls, module_name):
        """
        Retrieve the module_id by providing the module_name.
        :param module_name: The name of the module as a string.
        :return: The corresponding module_id or None if not found.
        """
        if not module_name:
            return None

        cleaned_input = module_name.strip().lower()
        for module in cls:
            if module.DESCRIPTION.strip().lower() == cleaned_input:
                return module.CODE
        return None

    @classmethod
    def get_module_name_by_id(cls, module_id):
        """
        Retrieve the module_name by providing the module_id.
        :param module_id: The ID of the module.
        :return: The corresponding module_name or None if not found.
        """
        if not module_id:
            return None

        for module in cls:
            if module.value[0] == module_id:
                return module.value[1]
        return None

    @classmethod
    def choices(cls):
        """
        Generate choices for Django model fields.
        :return: List of tuples (code, description.
        """

        return [(module.CODE, module.DESCRIPTION) for module in cls]

class ShipmentStatusEnum(BaseEnum):
    DRAFT = (5, "Draft")
    BOOKED = (10, "Booked")
    CONFIRMED = (15, "Confirmed")
    SHIPPED = (25, "Shipped")
    MODIFIED = (20, "Modified")
    CANCELLED = (30, "Cancelled")

class TransportModeEnum(BaseEnum):
    OCEAN = (5, "Ocean")
    AIR = (10, "Air")
    Road = (15, "Road")
    RAIL = (20, "Rail")

class ServiceTypeEnum(BaseEnum):
    CY = (5, "CY")
    CFS = (10, 'CFS')

class CargoTypeEnum(BaseEnum):
    NORMAL = (5, "Normal")
    REEFER = (10, "Reefer")
    DG = (15, "Dangerous Goods")

class CompanyTypeEnum(BaseEnum):
    """
    Enum representing the type of logistics company:
    """
    VENDOR = (5, "Vendor")
    ORIGIN_AGENT = (10, "Origin_agent")
    DESTINATION_AGENT = (15, "Destination_agent")
    CUSTOMER = (20, "Customer")
    SUPPLIER = (25, "Supplier")

class IncotermEnum(BaseEnum):
    EXW = (5, "ExWorks")
    FOB = (10, "FreeOnBoard")
    FCA = (15, "FreeCarrier")
    DAP = (20, "DeliveredAtPlace")
    FAS = (25, "Free Alongside Ship")
    CFR = (30, "Cost and Freight")
    CIS = (35, "Cost, Insurance and Freight")
    CPT = (40, "Carriage Paid To")
    CIP = (45, "Carriage and Insurance Paid To")
    DAF = (50, "Delivered At Frontier")
    DPU = (55, "Delivered at Place Unloaded")
    DDP = (60, "Delivered Duty Paid")
    DDU = (65, "Delivered Duty Unpaid")

class PaymentTermsEnum(BaseEnum):
    PREPAID = (5, "Prepaid")
    COLLECT = (10, "Collect")

def enum_search_q(enum_cls, field_name, search_value):
    """
    Builds a Q() object for enum name/description search.
    """
    code = enum_cls.get_module_id_by_name(search_value)
    if code is not None:
        return Q(**{field_name: code})
    return Q()

def build_global_search_q(search_value):
    q = Q()
    if not search_value:
        return q

    search_value = search_value.strip()
    search_lower = search_value.lower()

    # ---------------- TEXT SEARCH ----------------
    q |= Q(vendor_booking_number__icontains=search_value)
    q |= Q(shipper__icontains=search_value)
    q |= Q(consignee__icontains=search_value)
    q |= Q(place_of_receipt__icontains=search_value)
    q |= Q(place_of_delivery__icontains=search_value)
    q |= Q(vessel_name__icontains=search_value)
    q |= Q(customer__name__icontains=search_value)
    q |= Q(vendor__name__icontains=search_value)
    q |= Q(origin_agent__name__icontains=search_value)
    q |= Q(destination_agent__name__icontains=search_value)
    q |= Q(pol__name__icontains=search_value)
    q |= Q(pod__name__icontains=search_value)

    # ---------------- ENUM SEARCH ----------------
    enum_maps = {
        "vendor_booking_status": ShipmentStatusEnum,
        "transportation_mode": TransportModeEnum,
        "service_type": ServiceTypeEnum,
        "cargo_type": CargoTypeEnum,
        "incoterm": IncotermEnum,
        "payment_terms": PaymentTermsEnum,
    }

    for field, enum_cls in enum_maps.items():
        for enum_member in enum_cls:
            if search_lower in enum_member.DESCRIPTION.lower():
                q |= Q(**{field: enum_member.CODE})

    # ---------------- FLOAT SEARCH (EXACT) ----------------
    try:
        if re.match(r"^\d+\.$", search_value) or re.match(r"^\d+\.\d+$", search_value):
            base = float(search_value)

            decimal_part = search_value.split(".")[1] if "." in search_value else ""
            precision = len(decimal_part)

            tolerance = 10 ** (-precision) if precision > 0 else 1

            min_value = base
            max_value = base + tolerance

            q |= (
                    Q(volume_booked__gte=min_value, volume_booked__lt=max_value) |
                    Q(volume_actual__gte=min_value, volume_actual__lt=max_value) |
                    Q(weight_booked__gte=min_value, weight_booked__lt=max_value) |
                    Q(weight_actual__gte=min_value, weight_actual__lt=max_value) |
                    Q(quantity_booked__gte=min_value, quantity_booked__lt=max_value) |
                    Q(quantity_actual__gte=min_value, quantity_actual__lt=max_value)
            )
    except ValueError:
        pass

    # ---------------- INTEGER SEARCH ----------------
    if search_value.isdigit():
        int_value = int(search_value)

        q |= Q(vendor_booking_status=int_value)
        q |= Q(transportation_mode=int_value)
        q |= Q(service_type=int_value)
        q |= Q(cargo_type=int_value)
        q |= Q(incoterm=int_value)
        q |= Q(payment_terms=int_value)
        q |= Q(equipment_count=int_value)

        q |= Q(volume_booked=int_value)
        q |= Q(volume_actual=int_value)
        q |= Q(weight_booked=int_value)
        q |= Q(weight_actual=int_value)
        q |= Q(quantity_booked=int_value)
        q |= Q(quantity_actual=int_value)

        if len(search_value) == 4:
            q |= Q(created_on__year=int_value)
            q |= Q(cargo_readiness_date__year=int_value)

        if search_value.isdigit() and len(search_value) == 2:
            int_value = int(search_value)

            # Month: 01–12
            if 1 <= int_value <= 12:
                q |= Q(created_on__month=int_value)
                q |= Q(cargo_readiness_date__month=int_value)

            # Day: 01–31
            if 1 <= int_value <= 31:
                q |= Q(created_on__day=int_value)
                q |= Q(cargo_readiness_date__day=int_value)

    # ---------------- YEAR-MONTH ----------------
    ym = parse_year_month(search_value)
    if ym:
        if ym:
            year, month = ym
            q |= Q(created_on__year=year, created_on__month=month)
            q |= Q(cargo_readiness_date__year=year, cargo_readiness_date__month=month)


    # ---------------- DAY-MONTH (DD/MM) ----------------
    dm = parse_day_month(search_value)
    if dm:
        month, day = dm
        q |= Q(created_on__month=month, created_on__day=day)
        q |= Q(cargo_readiness_date__month=month, cargo_readiness_date__day=day)

    # ---------------- FULL DATE ----------------
    try:
        parsed_date = parse_search_date(search_value)
        q |= Q(created_on__date=parsed_date)
        q |= Q(cargo_readiness_date__date=parsed_date)
    except ValueError:
        pass

    # ---------------- BOOLEAN ----------------
    if search_lower in ("active", "true"):
        q |= Q(is_active=True)
    elif search_lower in ("inactive", "false"):
        q |= Q(is_active=False)

    return q

def apply_fk_filter(queryset, field, value):
    """
    field = FK field name on ShipmentOrder
    value = id OR name
    """
    if not value:
        return queryset

    # ID filter
    if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
        return queryset.filter(**{f"{field}_id": int(value)})

    # Name filter
    return queryset.filter(**{f"{field}__name__icontains": value})