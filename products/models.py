# Models live in the project-level models/ package; this module
# registers them with Django for the "products" app.
from models.product import Product, ProductImage  # noqa: F401
