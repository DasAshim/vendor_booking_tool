from django.urls import path
from . import views

urlpatterns = [
    path('v1/role/list', views.RoleFilterApi.as_view(), name='role_list'),
    path('v1/role', views.RoleCreateApi.as_view(), name='role_create'),
    path('v1/role/<int:pk>', views.RoleUpdateApi.as_view(), name='role_update'),
    path('v1/role/user', views.RoleUserCreateAPI.as_view(), name='role_user_create'),
    path('v1/privilege/list', views.RolePermissionFilterApi.as_view(), name='privilege_list')
]
