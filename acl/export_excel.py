import io
from datetime import datetime
import logging
import xlsxwriter
from datetime import datetime
from django.http import HttpResponse
from dateutil.parser import isoparse
import logging
from rest_framework import status
from rest_framework.response import Response


logger = logging.getLogger(name="CARGO_PLAN")

MODULES = {
    "ROLE_MANAGEMENT": {
        "Role Name": {"value": "role_name"},
        "Role Description": {"value": "role_description"},
        "Created On(UTC)": {"value": "created_on"},
        "Created By": {"value": "created_by"}, "Modified On(UTC)": {"value": "modified_on"},
        "Modified By": {"value": "modified_by"}
    },
    "USER_MANAGEMENT": {
        "Status": {
            "value": "is_active",
            "convert": {1: "Active", 0: "Inactive"}
        },
        "Email": {"value": "email"},
        "First Name": {"value": "first_name"},
        "Last Name": {"value": "last_name"},
        "Company Name": {"value": "organization_name"},
        "Role": {"value": "role_data"},
        "Phone Number": {"value": "phone_number"},
        "Legal Entity Allocation": {"value": "legal_entity_data"},
        "Last Login (UTC)": {"value": "last_login"},
        "Created On(UTC)": {"value": "created_on"},
        "Created By": {"value": "created_by"},
        "Modified On(UTC)": {"value": "modified_on"},
        "Modified By": {"value": "modified_by"}
    },
    "TRADING_PARTNER_SETUP": {
        "Status": {
            "value": "is_active",
            "convert": {1: "Active", 0: "Inactive"}
        },
        "File Format": {"value": "file_format"},
        "TP Profile Name": {"value": "profile_name"},
        "Sender ID": {"value": "sender_id"},
        "Receiver ID": {"value": "receiver_id"},
        "Sender Name": {"value": "sender_name"},
        "Receiver Name": {"value": "receiver_name"},
        "Message Type": {"value": "message_type"},
        "Message Version": {"value": "message_version"},
        "Message Direction": {
            "value": "message_direction",
            "convert": {"I": "IN", "O": "OUT"}
        },
        "Acknowledgement Flag": {
            "value": "acknowledgement_flag",
             "convert": {True: "Yes", False: "No"}
        },
        "PDF Required": {
            "value": "pdf_required",
            "convert": {True: "Yes", False: "No"}
        },
        "Allow Duplicate": {
            "value": "allow_duplicate_flag",
            "convert": {True: "Yes", False: "No"}
        },
        "Email ID": {"value": "email_id"},
        "Contact No.": {"value": "contact_number"},
        "Created By": {"value": "created_by"},
        "Created On(UTC)": {"value": "created_on"},
        "Modified By": {"value": "modified_by"},
        "Modified On(UTC)": {"value": "modified_on"}
    },
    "CODE_LIST_SETUP": {
        "Table Name": {"value": "name"},
        "Description": {"value": "description"},
        "Created By": {"value": "created_by"},
        "Created On(UTC)": {"value": "created_on"},
        "Modified By": {"value": "modified_by"},
        "Modified On(UTC)": {"value": "modified_on"}
    },
    "CONNECTIVITY": {
        "Status": {
            "value": "is_active",
            "convert": {1: "Active", 0: "Inactive"}
        },
        "Connectivity Name": {"value": "connectivity_name"},
        "Connectivity Type": {
            "value": "connectivity_type_id",
            "convert": {
                5: "SFTP",
                10: "SFTP",
                15: "API",
                20: "ESB",
                25: "AS2",
                30: "FSA",
                35: "SMTP"
            }
        },
        "Message Direction": {
            "value": "direction",
            "convert": {"I": "IN", "O": "OUT"}
        },
        "Payload": {"value": "payload"},
        "Created By": {"value": "created_by"},
        "Created On(UTC)": {"value": "created_on"},
        "Action By": {"value": "modified_by"},
        "Action On(UTC)": {"value": "modified_on"}
    },

    "CODELIST_LIBRARY": {
        "Sender ID": {"value": "sender_id"},
        "Receiver ID": {"value": "receiver_id"},
        "Message Type": {"value": "message_type"},
        "Lookup Value": {"value": "lookup_value"},
        "Replace Value 1": {"value": "text1"},
        "Replace Value 2": {"value": "text2"},
        "Replace Value 3": {"value": "text3"},
        "Replace Value 4": {"value": "text4"},
        "Replace Value 5": {"value": "text5"},
        "Replace Value 6": {"value": "text6"},
        "Replace Value 7": {"value": "text7"}
    },
    "RULES_SETUP": {
        "Rule Name": {"value": "rule_name"},
        "Outer Rule Tag": {"value": "output_tag"},
        "In Rule Tag": {"value": "input_tag"},
        "Input Path": {"value": "input_path"},
        "Code List": {"value": "codelist_name"},
        "Hardcode Value": {"value": "default_value"},
        "Data Separator": {"value": "data_separator"}
    },
}

master_module = {
    10: "DOCUMENT_TRACKER", 20: "E_TRACKER", 30: "DASHBOARD", 40: "LEGAL_ENTITY_MDM", 50: "PO_MDM", 60: "VENDOR_MDM",
    70: "VAT_ALIAS", 80: "NAME_ALIAS", 90: "ZIP_ALIAS", 100: "CITY_ALIAS", 110: "CURRENCY_MDM", 120: "CURRENCY_ALIAS",
    130: "USER_MANAGEMENT", 140: "ROLE_MANAGEMENT", 150: "PO_PREFIX_MANAGEMENT", 160: "DOCUMENT_ACTION_MANAGEMENT",
    170: "ERROR_CODE_LIST", 180: "LANGUAGE_INTENT_ALIAS", 190: "CUSTOM_PROFILE_LIST",
    200: "EMAIL_TEMPLATE", 210: "APPLICATION_CONFIGURATION", 220: "ANNOUNCEMENT_MANAGEMENT",
    230: "DOCUMENT_TRACKER_LINE", 240: "TRADING_PARTNER_MANAGEMENT", 250: "TRADING_PARTNER_RULE_MANAGEMENT",
    260: "CODELIST_MANAGEMENT", 270: "CONNECTIVITY_MANAGEMENT", 280: "USER_PREFERENCE", 290: "DOCUMENT_TYPE_MANAGEMENT",
    300: "BLACKLIST_EMAIL", 310: "EINVOICE_PARTNER_MANAGEMENT", 320: "EINVOICE_RULE_MANAGEMENT"
}


def parse_datetime(value):
    try:
        parsed_datetime = isoparse(value)
        return parsed_datetime.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.info(f"Error parsing datetime: {e}")
        return str(value)


def get_value_from_key(field, item, module_name, header_value):
    if field == "profile_type":
        value = item.get(field)
        value = value[0].get("profile_name")
    elif module_name == "DATA_CHANGE_LOGGER" and field == "application_module_id":
        value = item.get(field)
        value = master_module.get(value)
    elif module_name == "USER_MANAGEMENT" and field == "role_data":
        value = item.get(field)
        value = value[0].get("role_name")
    elif module_name == "USER_MANAGEMENT" and field == "legal_entity_data":
        value = item.get(field)
        value = ','.join(str(item['legal_entity_id']) for item in value)
    else:
        value = item.get(field)

    converted_value = header_value.get("convert", {}).get(value)
    if converted_value:
        value = converted_value

    return value if value else ""


def export_query_to_excel(data, module_name, file_name=""):
    try:
        if not file_name:
            now_str = datetime.now().strftime('%Y%m%d%H%M%S')
            file_name = f"EXPORT_{module_name}_{now_str}.xlsx"
        headers = MODULES.get(module_name)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet("Export_Report")

        # Write header row with field names
        header_format = workbook.add_format({'bold': True})
        for col, field in enumerate(headers.keys()):
            worksheet.write(0, col, field, header_format)

        # Write data rows
        for row, item in enumerate(data, start=1):
            for col, header in enumerate(headers.keys()):
                header_value = headers.get(header)
                field = header_value.get("value")
                if not field:
                    continue

                value = get_value_from_key(field, item, module_name, header_value)

                if field in ["modified_on", "created_on", "time_stamp", "action_on",
                             "last_login", "last_used_on"] and value:
                    value = parse_datetime(value)

                worksheet.write(row, col, value)

        # Close workbook and get output as bytes
        workbook.close()
        excel_data = output.getvalue()

        # Create a response with Excel content type and attachment
        response = HttpResponse(excel_data, content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        response['Access-Control-Allow-Origin'] = '*'
        response["Access-Control-Expose-Headers"] = "*"

        return response

    except Exception as e:
        return Response({"message": f"Failed to export due to {e}"}, status=status.HTTP_400_BAD_REQUEST)
