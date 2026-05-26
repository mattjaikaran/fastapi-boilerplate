import factory
from factory import Faker

from app.api.users.model import User, UserRole
from app.core.security.password import get_password_hash


class UserFactory(factory.Factory):
    class Meta:
        model = User

    email = Faker("email")
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    hashed_password = factory.LazyFunction(lambda: get_password_hash("password123"))
    role = UserRole.user
    is_active = True
    is_email_verified = True


class AdminUserFactory(UserFactory):
    role = UserRole.admin
    email = Faker("email")
