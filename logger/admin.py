from django.contrib import admin
from .models import AccessLog, ErrorLog

@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("id", "path", "method", "status_code", "user_id", "created_on")
    search_fields = ("path", "user_id", "status_code")
    list_filter = ("status_code", "method")

@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = ("id", "path", "method", "status_code", "user_id", "created_on")
    search_fields = ("path", "user_id", "status_code")
    list_filter = ("status_code", "method")
