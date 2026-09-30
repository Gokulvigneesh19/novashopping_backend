# Models live in the project-level models/ package; this module
# registers them with Django for the "wishlist" app.
from models.wishlist import Wishlist, WishlistItem  # noqa: F401
