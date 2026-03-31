from django.db import models
from vendor_booking_tool.utility import BaseUserModel

# Create your models here.

class AccessLog(BaseUserModel):
    user_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.PositiveIntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    request_body = models.JSONField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True, help_text="Request duration in milliseconds")

    class Meta:
        db_table = 'ACCESS_LOGS'
        ordering = ["-created_on"]
        verbose_name_plural = "Access Logs"
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["path"]),
            models.Index(fields=["status_code"]),
            models.Index(fields=["created_on"]),
            models.Index(fields=["user_id", "created_on"]),
        ]

    def __str__(self):
        return f"{self.method}{self.path}{self.status_code}"


class ErrorLog(BaseUserModel):
    user_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.PositiveIntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    request_body = models.JSONField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True, help_text="Request duration in milliseconds")

    class Meta:
        db_table = 'ERROR_LOGS'
        ordering = ["-created_on"]
        verbose_name_plural = "Error Logs"
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["path"]),
            models.Index(fields=["status_code"]),
            models.Index(fields=["created_on"]),
            models.Index(fields=["user_id", "created_on"]),
        ]

    def __str__(self):
        return f"{self.method}{self.path}{self.status_code}"