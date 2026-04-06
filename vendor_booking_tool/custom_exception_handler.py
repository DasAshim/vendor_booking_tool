from rest_framework.views import exception_handler


def error_handler(exc, context):
    response = exception_handler(exc, context)

    if response and response.status_code == 400:
        response.data = process_bad_request(response.data)

    if response and isinstance(response.data, dict) and "detail" in response.data:
        message = response.data.pop('detail')
        if message == "User with email email already exists.":
            message = "User with this email already exists. Email should be unique."
        response.data['message'] = message

    elif response and isinstance(response.data, dict) and "email" in response.data.get("error", ""):
        message = response.data.pop('message', "")
        if message == "User with email email already exists.":
            message = "User with this email already exists. Email should be unique."
        response.data['message'] = message

    return response


def process_bad_request(data):
    if isinstance(data, list):
        return format_list_error(data)
    if isinstance(data, str):
        return {'message': data, "error": data}
    if isinstance(data, dict):
        return format_dict_error(data)
    return data


def format_list_error(data):
    error = ", ".join(data)
    return {'message': error, "error": data}


def format_dict_error(data):
    try:
        first_key, first_value = list(data.items())[0]
        message = extract_message(first_key, first_value)
    except Exception as ex:
        print(ex)
        message = "something went wrong"
    return {'message': message, "error": data}


def extract_message(first_key, first_value):
    if isinstance(first_value, list):
        message = first_value[0]
        return format_message(message, first_key)
    if isinstance(first_value, str):
        return first_value
    return "something went wrong"


def format_message(message, first_key):
    if message.startswith(f"This {first_key}"):
        message = message.replace("This ", "")
    return message.replace("this", first_key).replace("This", first_key)
