import json
import time
from django.db.models.signals import pre_delete
from logger.models import ErrorLog


class ErrorLoggerMiddleware:
    """
    Middleware to capture and log all 5xx errors or unhandled exceptions
    into the ErrorLog model for debugging and auditing.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.deleted_instance = None
        pre_delete.connect(self.store_deleted_instance)

    def store_deleted_instance(self, sender, instance, **kwargs):
        """Capture deleted instance data (optional)."""
        self.deleted_instance = instance.__dict__

    def __call__(self, request):
        start_time = time.time()
        request_data = self.extract_request_data(request)

        try:
            response = self.get_response(request)
        except Exception as ex:
            # Log the unhandled exception
            duration = round((time.time() - start_time) * 1000, 2)
            self.log_error(
                request=request,
                response=None,
                request_data=request_data,
                error=str(ex),
                duration=duration,
            )
            # Re-raise to allow Django to return proper error response
            raise

        # Log if status code indicates a server error (5xx)
        if 500 <= response.status_code <= 599:
            duration = round((time.time() - start_time) * 1000, 2)
            self.log_error(
                request=request,
                response=response,
                request_data=request_data,
                duration=duration,
            )

        return response

    def extract_request_data(self, request):
        """Safely extract the request body based on method and content type."""
        request_data = {}
        try:
            if request.method == "GET":
                request_data = {k: v for k, v in request.GET.items()}
            elif request.method in ["POST", "PUT", "PATCH", "DELETE"]:
                if request.content_type and "application/json" in request.content_type:
                    request_data = json.loads(request.body.decode())
                elif hasattr(request, "POST"):
                    request_data = {k: v for k, v in request.POST.items()}
        except Exception as e:
            print(f"[ErrorLog] Error extracting request data: {e}")
        return request_data

    def log_error(self, request, response=None, request_data=None, error=None, traceback_str=None, duration=None):
        """Log 5xx responses and unhandled exceptions to ErrorLog."""
        try:
            user_id = getattr(request.user, "id", None)

            response_body = ""
            if response is not None:
                try:
                    if hasattr(response, "content"):
                        response_body = response.content.decode(errors="replace")
                except Exception:
                    response_body = "Non-decodable response"
            elif error:
                response_body = {
                    "error": error,
                    "traceback": traceback_str,
                }

            ErrorLog.objects.create(
                user_id=user_id,
                path=request.path,
                method=request.method,
                status_code=response.status_code if response else 500,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                request_body=request_data or {},
                response_body=response_body,
                duration=duration,
            )
        except Exception as e:
            print(f"[ErrorLog] Failed to log error: {e}")

    @staticmethod
    def get_client_ip(request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
