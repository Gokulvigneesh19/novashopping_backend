# Models live in the project-level models/ package; this module
# registers them with Django for the "cart" app.
from models.cart import Cart, CartItem  # noqa: F401
