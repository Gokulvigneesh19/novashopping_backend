# Models live in the project-level models/ package; this module
# registers them with Django for the "users" app.
from models.user import User, UserManager  # noqa: F401
