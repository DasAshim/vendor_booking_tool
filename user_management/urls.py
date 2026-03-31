from django.urls import path

from . import views

urlpatterns = [

    path('v1/register',views.UserRegisterApi.as_view(),
         name='user_register'),
    path('v1/list', views.UserFilterApi.as_view(), name='user_list'),
    path('v1/detail/<int:pk>', views.UserDetailApi.as_view(), name='user_details'),
    path('v1/short-info/<int:pk>', views.UserShortInfoApi.as_view(), name='user_short_details'),
    path('v1/profile', views.UserProfileApi.as_view(), name='user_profile'),
    path('v1/<int:pk>', views.UserModifyApi.as_view(), name='user_modify'),

    path('v1/json-info', views.UserJsonDataAPI.as_view(), name='user_details_json'),

    path('v1/user/profile/access/<int:user_id>', views.UserProfileAccessApi.as_view(), name='user_access_profile'),

    path('v1', views.UserCreatePrivilegeApi.as_view(),
         name='user_application_permission_create'),
    path('v1/modify/<int:pk>', views.UserUpdatePrivilegeApi.as_view(),
         name='user_application_permission_update'),
    path('v1/superuser/modify/<int:pk>', views.UserUpdateIsSuperUserApi.as_view(), name='super_user_update'),
]
