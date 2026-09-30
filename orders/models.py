# Models live in the project-level models/ package; this module
# registers them with Django for the "orders" app.
from models.order import Order, OrderItem  # noqa: F401
