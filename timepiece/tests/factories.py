import datetime
from dateutil.relativedelta import relativedelta
import factory
from factory.fuzzy import FuzzyDate, FuzzyInteger

from django.contrib.auth import models as auth

from timepiece.contracts import models as contracts
from timepiece.crm import models as crm
from timepiece.entries import models as entries
from timepiece import utils


class BaseUserFactory(factory.DjangoModelFactory):
    FACTORY_FOR = auth.User

    username = factory.Sequence(lambda n: 'user{0}'.format(n))
    email = factory.Sequence(lambda n: 'user{0}@example.com'.format(n))
    password = 'password'

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if cls.FACTORY_DJANGO_GET_OR_CREATE:
            return cls._get_or_create(target_class, *args, **kwargs)

        manager = cls._get_manager(target_class)
        is_staff = kwargs.pop('is_staff', False)
        is_superuser = kwargs.pop('is_superuser', False)

        if is_superuser:
            return manager.create_superuser(*args, **kwargs)

        elif is_staff:
            user = manager.create_user(*args, **kwargs)
            user.is_staff = True
            user.is_active = True
            user.is_superuser = False
            user.save()
            return user

        else:
            return manager.create_user(*args, **kwargs)


class UserFactory(BaseUserFactory):
    pass


class SuperuserFactory(BaseUserFactory):
    is_superuser = True
    is_staff = True


class GroupFactory(factory.DjangoModelFactory):
    FACTORY_FOR = auth.Group

    name = factory.Sequence(lambda n: 'group{0}'.format(n))


class ProjectContractFactory(factory.DjangoModelFactory):
    FACTORY_FOR = contracts.ProjectContract

    name = factory.Sequence(lambda n: 'contract{0}'.format(n))
    start_date = datetime.date.today()
    end_date = datetime.date.today() + relativedelta(weeks=2)
    status = contracts.ProjectContract.STATUS_CURRENT,
    type = contracts.ProjectContract.PROJECT_PRE_PAID_HOURLY


class ContractHourFactory(factory.DjangoModelFactory):
    FACTORY_FOR = contracts.ContractHour

    date_requested = datetime.date.today()
    status = contracts.ContractHour.APPROVED_STATUS
    contract = factory.SubFactory('timepiece.tests.factories.ProjectContractFactory')


class ContractAssignmentFactory(factory.DjangoModelFactory):
    FACTORY_FOR = contracts.ContractAssignment

    user = factory.SubFactory('timepiece.tests.factories.UserFactory')
    contract = factory.SubFactory('timepiece.tests.factories.ProjectContractFactory')
    start_date = datetime.date.today()
    end_date = datetime.date.today() + relativedelta(weeks=2)


class HourGroupFactory(factory.DjangoModelFactory):
    FACTORY_FOR = contracts.HourGroup

    name = factory.Sequence(lambda n: 'hourgroup{0}'.format(n))


class EntryGroupFactory(factory.DjangoModelFactory):
    FACTORY_FOR = contracts.EntryGroup

    user = factory.SubFactory('timepiece.tests.factories.UserFactory')
    project = factory.SubFactory('timepiece.tests.factories.ProjectFactory')
    end = FuzzyDate(datetime.date.today() - relativedelta(months=1))

class TypeAttributeFactory(factory.DjangoModelFactory):
    FACTORY_FOR = crm.Attribute

    label = factory.Sequence(lambda n: 'type{0}'.format(n))
    type = crm.Attribute.PROJECT_TYPE


class StatusAttributeFactory(factory.DjangoModelFactory):
    FACTORY_FOR = crm.Attribute

    label = factory.Sequence(lambda n: 'status{0}'.format(n))
    type = crm.Attribute.PROJECT_STATUS


class BusinessFactory(factory.DjangoModelFactory):
    FACTORY_FOR = crm.Business

    name = factory.Sequence(lambda n: 'business{0}'.format(n))


class BaseProjectFactory(factory.DjangoModelFactory):
    FACTORY_FOR = crm.Project

    name = factory.Sequence(lambda n: 'project{0}'.format(n))
    business = factory.SubFactory('timepiece.tests.factories.BusinessFactory')
    point_person = factory.SubFactory('timepiece.tests.factories.UserFactory')


class ProjectFactory(BaseProjectFactory):
    type = factory.SubFactory('timepiece.tests.factories.TypeAttributeFactory')
    status = factory.SubFactory('timepiece.tests.factories.StatusAttributeFactory')


class BillableProjectFactory(BaseProjectFactory):
    type = factory.SubFactory('timepiece.tests.factories.TypeAttributeFactory', billable=True)
    status = factory.SubFactory('timepiece.tests.factories.StatusAttributeFactory', billable=True)


class NonbillableProjectFactory(BaseProjectFactory):
    type = factory.SubFactory('timepiece.tests.factories.TypeAttributeFactory', billable=False)
    status = factory.SubFactory('timepiece.tests.factories.StatusAttributeFactory', billable=False)


class RelationshipTypeFactory(factory.DjangoModelFactory):
    FACTORY_FOR = crm.RelationshipType

    name = factory.Sequence(lambda n: 'reltype{0}'.format(n))


class ProjectRelationshipFactory(factory.DjangoModelFactory):
    FACTORY_FOR = crm.ProjectRelationship

    user = factory.SubFactory('timepiece.tests.factories.UserFactory')
    project = factory.SubFactory('timepiece.tests.factories.ProjectFactory')


class UserProfileFactory(factory.DjangoModelFactory):
    FACTORY_FOR = crm.UserProfile

    user = factory.SubFactory('timepiece.tests.factories.UserFactory')

class ActivityFactory(factory.DjangoModelFactory):
    FACTORY_FOR = entries.Activity

    code = factory.Sequence(lambda n: 'a{0}'.format(n))
    name = factory.Sequence(lambda n: 'activity{0}'.format(n))


class ActivityGroupFactory(factory.DjangoModelFactory):
    FACTORY_FOR = entries.ActivityGroup

    name = factory.Sequence(lambda n: 'activitygroup{0}'.format(n))


class LocationFactory(factory.DjangoModelFactory):
    FACTORY_FOR = entries.Location

    name = factory.Sequence(lambda n: 'location{0}'.format(n))
    slug = factory.Sequence(lambda n: 'location{0}'.format(n))


class EntryFactory(factory.DjangoModelFactory):
    FACTORY_FOR = entries.Entry

    status = entries.Entry.UNVERIFIED
    user = factory.SubFactory('timepiece.tests.factories.UserFactory')
    activity = factory.SubFactory('timepiece.tests.factories.ActivityFactory')
    project = factory.SubFactory('timepiece.tests.factories.ProjectFactory')
    location = factory.SubFactory('timepiece.tests.factories.LocationFactory')


class ProjectHoursFactory(factory.DjangoModelFactory):
    FACTORY_FOR = entries.ProjectHours

    week_start = utils.get_week_start()
    project = factory.SubFactory('timepiece.tests.factories.ProjectFactory')
    user = factory.SubFactory('timepiece.tests.factories.UserFactory')
    hours = FuzzyInteger(0, 20)
