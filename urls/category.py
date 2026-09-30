from django.urls import path

from views import CategoryProductsView, CategoryView


urlpatterns = [
    path("", CategoryView.as_view(), name="categories"),
    path("<uuid:category_id>/", CategoryView.as_view(), name="category-detail"),
    path("<uuid:category_id>/products/", CategoryProductsView.as_view(), name="category-products"),
]
