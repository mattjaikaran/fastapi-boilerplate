import uuid
from datetime import UTC, datetime

import factory
from factory import Faker

from app.api.organizations.model import OrgRole, Organization, OrganizationMember


class OrganizationFactory(factory.Factory):
    class Meta:
        model = Organization

    id = factory.LazyFunction(uuid.uuid4)
    owner_id = factory.LazyFunction(uuid.uuid4)
    name = Faker("company")
    slug = factory.LazyAttribute(lambda o: o.name.lower().replace(" ", "-").replace(",", "")[:50])
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))


class OrganizationMemberFactory(factory.Factory):
    class Meta:
        model = OrganizationMember

    id = factory.LazyFunction(uuid.uuid4)
    organization_id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    role = OrgRole.member
    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))
