from django.urls import path

from .views import PortOfLoadingCreateApiView, PortOfLoadingModifyApiView, PortOfLoadingFilterApiView, \
    PortOfPortOfDestinationCreateApiView, PortOfDestiationFilterApiView, PortOfDestinationModifyApiView, \
    CarrierCreateApiView, CarrierModifyApiView, CarrierFilterApiView

urlpatterns = [
    path('v1/create_pol',PortOfLoadingCreateApiView.as_view(),name='port-creation'  ),
    path('v1/update_pol/<int:pk>',PortOfLoadingModifyApiView.as_view(),name='port-update'),
    path('v1/filter_pol',PortOfLoadingFilterApiView.as_view(),name='port-filter'),
#     ---
    path('v1/create_pod',PortOfPortOfDestinationCreateApiView.as_view(),name='port-creation' ),
    path('v1/update_pod/<int:pk>',PortOfDestinationModifyApiView.as_view(),name='port-update'),
    path('v1/filter_pod',PortOfDestiationFilterApiView.as_view(),name='port-filter'),

#     -----
    path('v1/create_carrier',CarrierCreateApiView.as_view(),name='carrier-creation' ),
    path('v1/modify_carrier/<int:pk>',CarrierModifyApiView.as_view(),name='carrier-update'),
    path('v1/filter_carrier',CarrierFilterApiView.as_view(),name='carrier-filter'),
]