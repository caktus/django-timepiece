import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import factory
from factory.fuzzy import FuzzyDate, FuzzyInteger
import random

import six

from django.contrib.auth import models as auth
from django.contrib.auth.hashers import make_password

from timepiece.contracts import models as contracts
from timepiece.crm import models as crm
from timepiece.entries import models as entries
from timepiece import utils


class User(factory.DjangoModelFactory):

    class Meta:
        model = auth.User

    # FIXME: Some tests depend on first_name/last_name being unique.
    first_name = factory.Sequence(lambda n: 'Sam{0}'.format(n))
    last_name = factory.Sequence(lambda n: 'Blue{0}'.format(n))
    username = factory.Sequence(lambda n: 'user{0}'.format(n))
    email = factory.Sequence(lambda n: 'user{0}@example.com'.format(n))
    password = factory.LazyAttribute(lambda n: make_password('password'))

    @factory.post_generation
    def permissions(self, create, extracted, **kwargs):
        if create and extracted:
            for perm in extracted:
                if isinstance(perm, six.string_types):
                    app_label, codename = perm.split('.')
                    perm = auth.Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename,
                    )
                self.user_permissions.add(perm)


class Superuser(User):
    is_superuser = True
    is_staff = True


class Group(factory.DjangoModelFactory):

    class Meta:
        model = auth.Group

    name = factory.Sequence(lambda n: 'group{0}'.format(n))


class ProjectContract(factory.DjangoModelFactory):

    class Meta:
        model = contracts.ProjectContract

    name = factory.Sequence(lambda n: 'contract{0}'.format(n))
    start_date = datetime.date.today()
    end_date = datetime.date.today() + relativedelta(weeks=2)
    status = contracts.ProjectContract.STATUS_CURRENT,
    type = contracts.ProjectContract.PROJECT_PRE_PAID_HOURLY

    @factory.post_generation
    def contract_hours(self, create, extracted, **kwargs):
        if create:
            num_hours = extracted or random.randint(10, 400)
            for i in range(2):
                ContractHour(contract=self, hours=Decimal(str(num_hours/2.0)))

    @factory.post_generation
    def projects(self, create, extracted, **kwargs):
        if create and extracted:
            self.projects.add(*extracted)


class ContractHour(factory.DjangoModelFactory):

    class Meta:
        model = contracts.ContractHour

    date_requested = datetime.date.today()
    status = contracts.ContractHour.APPROVED_STATUS
    contract = factory.SubFactory('timepiece.tests.factories.ProjectContract')


class ContractAssignment(factory.DjangoModelFactory):

    class Meta:
        model = contracts.ContractAssignment

    user = factory.SubFactory('timepiece.tests.factories.User')
    contract = factory.SubFactory('timepiece.tests.factories.ProjectContract')
    start_date = datetime.date.today()
    end_date = datetime.date.today() + relativedelta(weeks=2)


class HourGroup(factory.DjangoModelFactory):

    class Meta:
        model = contracts.HourGroup

    name = factory.Sequence(lambda n: 'hourgroup{0}'.format(n))


class EntryGroup(factory.DjangoModelFactory):

    class Meta:
        model = contracts.EntryGroup

    user = factory.SubFactory('timepiece.tests.factories.User')
    project = factory.SubFactory('timepiece.tests.factories.Project')
    end = FuzzyDate(datetime.date.today() - relativedelta(months=1))


class TypeAttribute(factory.DjangoModelFactory):

    class Meta:
        model = crm.Attribute

    label = factory.Sequence(lambda n: 'type{0}'.format(n))
    type = crm.Attribute.PROJECT_TYPE


class StatusAttribute(factory.DjangoModelFactory):

    class Meta:
        model = crm.Attribute

    label = factory.Sequence(lambda n: 'status{0}'.format(n))
    type = crm.Attribute.PROJECT_STATUS


class Business(factory.DjangoModelFactory):

    class Meta:
        model = crm.Business

    name = factory.Sequence(lambda n: 'business{0}'.format(n))


class Project(factory.DjangoModelFactory):

    class Meta:
        model = crm.Project

    name = factory.Sequence(lambda n: 'project{0}'.format(n))
    business = factory.SubFactory('timepiece.tests.factories.Business')
    point_person = factory.SubFactory('timepiece.tests.factories.User')
    type = factory.SubFactory('timepiece.tests.factories.TypeAttribute')
    status = factory.SubFactory('timepiece.tests.factories.StatusAttribute')


class BillableProject(Project):
    type = factory.SubFactory('timepiece.tests.factories.TypeAttribute', billable=True)
    status = factory.SubFactory('timepiece.tests.factories.StatusAttribute', billable=True)


class NonbillableProject(Project):
    type = factory.SubFactory('timepiece.tests.factories.TypeAttribute', billable=False)
    status = factory.SubFactory('timepiece.tests.factories.StatusAttribute', billable=False)


class RelationshipType(factory.DjangoModelFactory):

    class Meta:
        model = crm.RelationshipType

    name = factory.Sequence(lambda n: 'reltype{0}'.format(n))


class ProjectRelationship(factory.DjangoModelFactory):

    class Meta:
        model = crm.ProjectRelationship

    user = factory.SubFactory('timepiece.tests.factories.User')
    project = factory.SubFactory('timepiece.tests.factories.Project')


class UserProfile(factory.DjangoModelFactory):

    class Meta:
        model = crm.UserProfile

    user = factory.SubFactory('timepiece.tests.factories.User')


class Activity(factory.DjangoModelFactory):

    class Meta:
        model = entries.Activity

    code = factory.Sequence(lambda n: 'a{0}'.format(n))
    name = factory.Sequence(lambda n: 'activity{0}'.format(n))


class BillableActivityFactory(Activity):
    billable = True


class NonbillableActivityFactory(Activity):
    billable = False


class ActivityGroup(factory.DjangoModelFactory):

    class Meta:
        model = entries.ActivityGroup

    name = factory.Sequence(lambda n: 'activitygroup{0}'.format(n))


class Location(factory.DjangoModelFactory):

    class Meta:
        model = entries.Location

    name = factory.Sequence(lambda n: 'location{0}'.format(n))
    slug = factory.Sequence(lambda n: 'location{0}'.format(n))


class Entry(factory.DjangoModelFactory):

    class Meta:
        model = entries.Entry

    status = entries.Entry.UNVERIFIED
    user = factory.SubFactory('timepiece.tests.factories.User')
    activity = factory.SubFactory('timepiece.tests.factories.Activity')
    project = factory.SubFactory('timepiece.tests.factories.Project')
    location = factory.SubFactory('timepiece.tests.factories.Location')


class ProjectHours(factory.DjangoModelFactory):

    class Meta:
        model = entries.ProjectHours

    week_start = utils.get_week_start()
    project = factory.SubFactory('timepiece.tests.factories.Project')
    user = factory.SubFactory('timepiece.tests.factories.User')
    hours = FuzzyInteger(0, 20)
