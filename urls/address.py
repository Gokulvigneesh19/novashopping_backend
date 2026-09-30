from django.urls import path

from views import AddressView


urlpatterns = [
    path("", AddressView.as_view(), name="addresses"),
    path("<uuid:address_id>/", AddressView.as_view(), name="address-detail"),
]
