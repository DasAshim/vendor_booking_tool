import time
import json
from django.db.models.signals import pre_delete
from logger.models import AccessLog


EXCLUDED_PATHS = [
    "/swagger", "/swagger/", "/swagger/?format=openapi",
    "/static/", "/favicon.ico"
]

class AccessLoggerMiddleware:
    """
    Middleware to log every incoming HTTP request and outgoing response.
    Captures request path, method, status, timing, user info, etc.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.deleted_instance = None
        pre_delete.connect(self.store_deleted_instance)

    def store_deleted_instance(self, sender, instance, **kwargs):
        """Capture deleted instance data (optional)."""
        self.deleted_instance = instance.__dict__

    def __call__(self, request):
        if any(request.path.startswith(p) for p in EXCLUDED_PATHS):
            return self.get_response(request)

        start_time = time.time()
        request_data = self.extract_request_data(request)

        response = self.get_response(request)
        self.set_security_headers(response)

        if self.should_log(request, response):
            duration = round((time.time() - start_time) * 1000, 2)
            self.log_access(request, response, request_data, duration)

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
            print(f"[AccessLog] Error extracting request data: {e}")
        return request_data

    @staticmethod
    def set_security_headers(response):
        """Set basic security headers."""
        try:
            response["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
                "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
                "img-src 'self' https://cdn.jsdelivr.net data:;"
            )
            response["Permissions-Policy"] = "geolocation=()"
            response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        except Exception as e:
            print(f"[AccessLog] Header Error: {e}")

    @staticmethod
    def should_log(request, response):
        """
        Determine if logging should be performed.
        Skip OPTIONS, HEAD, and 5xx responses (those are handled by ErrorLogger).
        """
        if response.status_code >= 500:
            return False
        return request.method not in ["OPTIONS", "HEAD"]

    def log_access(self, request, response, request_data, duration):
        """Log the successful request to the AccessLog model."""
        try:
            user_id = getattr(request.user, "id", None)

            # Safely handle response body
            response_body = ""
            try:
                if hasattr(response, "content"):
                    response_body = response.content.decode(errors="replace")
            except Exception:
                response_body = "Non-decodable response"

            AccessLog.objects.create(
                user_id=user_id,
                path=request.path,
                method=request.method,
                status_code=response.status_code,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                request_body=request_data,
                response_body=response_body,
                duration=duration,
            )

        except Exception as e:
            print(f"[AccessLog] Error logging access: {e}")

    @staticmethod
    def get_client_ip(request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
