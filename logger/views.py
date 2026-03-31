# logger/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging


app_logger = logging.getLogger('application')


class TriggerErrorView(APIView):
    """
    Test endpoint to intentionally trigger an error
    for verifying ErrorLoggerMiddleware.
    """
    def get(self, request):
        1 / 0  # Intentional error to test logging
        return Response({"message": "You should not see this."}, status=status.HTTP_200_OK)


class TestApplicationLoggerView(APIView):
    """
    Test endpoint to generate application-level logs
    for verifying application logger configuration.
    """
    def get(self, request):
        app_logger.info("Application logger test started.")
        app_logger.debug("Debug message for tracing workflow.")
        app_logger.warning("This is a sample warning from application logger.")
        app_logger.error("Simulated error message in app logger.")
        app_logger.info("Application logger test completed successfully.")

        return Response(
            {"message": "Application logger test completed. Check application.log file."},
            status=status.HTTP_200_OK
        )