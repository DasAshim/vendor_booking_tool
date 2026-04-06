from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


def ok_response(request):
    data = {
        "message": "Application is up and running...",
        "status_code": 200
    }
    return JsonResponse(data, status=200)


class BothHttpAndHttpsSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        schema.schemes = ["http", "https"]
        return schema


schema_view = get_schema_view(
    openapi.Info(
        title="Vendor Booking Tool APIs",
        default_version='v1',
        description="Vendor Booking Tool APIs documentation for web application and mobile application integration",
    ),
    public=True,
    generator_class=BothHttpAndHttpsSchemaGenerator,

)

urlpatterns = [
    path('', ok_response, name='ok_response'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/admin/', admin.site.urls),
    path('acl/', include('acl.urls')),
    path('master_data_management/', include('master_data_management.urls')),
    # path('shipment_management/',include('shipement_management.urls')),
    path('user_management/', include('user_management.urls')),
    path('api/token', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),

]
