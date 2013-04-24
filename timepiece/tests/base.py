import datetime
import random
import string
import urllib

from dateutil.relativedelta import relativedelta
from decimal import Decimal

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone

from timepiece.contracts.models import ProjectContract, ContractHour,\
        ContractAssignment, EntryGroup, HourGroup
from timepiece.crm.models import Attribute, Business, Project,\
        ProjectRelationship, RelationshipType, UserProfile
from timepiece.entries.models import Activity, ActivityGroup, Location, Entry,\
        ProjectHours
from timepiece import utils


class TimepieceDataTestCase(TestCase):
    url_name = ''
    url_kwargs = {}
    url_args = {}
    get_kwargs = {}
    post_data = {}

    def _url(self, url_name=None, url_args=None, url_kwargs=None,
            get_kwargs=None):
        url_name = url_name or self.url_name
        url_args = self.url_args if url_args is None else url_args
        url_kwargs = self.url_kwargs if url_kwargs is None else url_kwargs
        get_kwargs = self.get_kwargs if get_kwargs is None else get_kwargs

        url = reverse(url_name, args=url_args, kwargs=url_kwargs)
        if get_kwargs:
            url = '{0}?{1}'.format(url, urllib.urlencode(get_kwargs))
        return url

    def _get(self, url_name=None, url_args=None, url_kwargs=None,
            get_kwargs=None, url=None, *args, **kwargs):
        """Convenience wrapper for self.client.get.

        If url is not passed, it is built using url_name, url_args, url_kwargs.
        Get parameters may be added from get_kwargs.
        """
        url = url or self._url(url_name, url_args, url_kwargs, get_kwargs)
        return self.client.get(path=url, *args, **kwargs)

    def _post(self, data=None, url_name=None, url_args=None,
            url_kwargs=None, get_kwargs=None, url=None, *args, **kwargs):
        """Convenience wrapper for self.client.post.

        If url is not passed, it is built using url_name, url_args, url_kwargs.
        Get parameters may be added from get_kwargs.
        """
        url = url or self._url(url_name, url_args, url_kwargs, get_kwargs)
        data = self.post_data if data is None else data
        return self.client.post(path=url, data=data, *args, **kwargs)

    def create_business(self, data=None):
        data = data or {}
        name = self.random_string(30, extra_chars=' ')
        defaults = {
            'name': name,
        }
        defaults.update(data)
        return Business.objects.create(**defaults)

    def random_string(self, length=255, extra_chars=''):
        chars = string.letters + extra_chars
        return ''.join([random.choice(chars) for i in range(length)])

    def create_project_type(self, data=None):
        data = data or {}
        defaults = {
            'label': self.random_string(30, extra_chars=' '),
            'type': 'project-type',
        }
        defaults.update(data)
        return Attribute.objects.create(**defaults)

    def create_project_status(self, data=None):
        data = data or {}
        defaults = {
            'label': self.random_string(24, extra_chars=' '),
            'type': 'project-status',
        }
        defaults.update(data)
        return Attribute.objects.create(**defaults)

    def create_project(self, billable=False, name=None, data=None):
        data = data or {}
        if not name:
            name = self.random_string(30, extra_chars=' ')
        defaults = {
            'name': name,
            'type': self.create_project_type(data={'billable': billable}),
            'status': self.create_project_status(data={'billable': billable}),
            'tracker_url': self.random_string(25),
        }
        defaults.update(data)
        if 'business' not in defaults:
            defaults['business'] = self.create_business()
        if 'point_person' not in defaults:
            defaults['point_person'] = self.create_user()
        return Project.objects.create(**defaults)

    def create_project_relationship(self, types=None, data=None):
        types = types or []
        data = data or {}
        defaults = {}
        defaults.update(data)
        if 'user' not in defaults:
            defaults['user'] = self.create_user()
        if 'project' not in defaults:
            defaults['project'] = self.create_project()
        relationship = ProjectRelationship.objects.create(**defaults)
        relationship.types.add(*types)
        return relationship

    def create_relationship_type(self, data=None):
        data = data or {}
        defaults = {
            'name': self.random_string(25),
        }
        defaults.update(data)
        return RelationshipType.objects.create(**defaults)

    def create_activity(self, activity_groups=None, data=None):
        activity_groups = activity_groups or []
        data = data or {}
        defaults = {
            'code': self.random_string(5, extra_chars=' '),
            'name': self.random_string(50, extra_chars=' '),
            'billable': False
        }
        defaults.update(data)
        activity = Activity.objects.create(**defaults)
        if activity_groups:
            activity.activity_group.add(*activity_groups)
            activity.save()
        return activity

    def create_location(self, data=None):
        data = data or {}
        defaults = {
            'name': self.random_string(255, extra_chars=' '),
            'slug': self.random_string(255),
        }
        defaults.update(data)
        return Location.objects.create(**defaults)

    def create_entry(self, data=None):
        data = data or {}
        defaults = {}
        defaults.update(data)
        if 'user' not in defaults:
            defaults['user'] = self.user
        if 'activity' not in defaults:
            defaults['activity'] = self.create_activity()
        if 'project' not in defaults:
            defaults['project'] = self.create_project()
        if 'location' not in defaults:
            defaults['location'] = self.create_location()
        if 'status' not in defaults:
            defaults['status'] = Entry.UNVERIFIED
        return Entry.objects.create(**defaults)

    def create_contract_hour(self, data=None):
        defaults = {
            'date_requested': datetime.date.today(),
            'status': ContractHour.APPROVED_STATUS
        }
        defaults.update(data or {})
        if not 'contract' in defaults:
            defaults['contract'] = self.create_contract()
        return ContractHour.objects.create(**defaults)

    def create_contract(self, projects=None, **kwargs):
        defaults = {
            'name': self.random_string(25),
            'start_date': datetime.date.today(),
            'end_date': datetime.date.today() + datetime.timedelta(weeks=2),
            'num_hours': random.randint(10, 400),
            'status': 'current',
            'type': ProjectContract.PROJECT_PRE_PAID_HOURLY,
        }
        defaults.update(kwargs)
        num_hours = defaults.pop('num_hours')
        contract = ProjectContract.objects.create(**defaults)
        contract.projects.add(*(projects or []))
        # Create 2 ContractHour objects that add up to the hours we want
        for i in (1, 2):
            self.create_contract_hour({
                'hours': Decimal(str(num_hours / 2.0)),
                'contract': contract,
                'status': ContractHour.APPROVED_STATUS
            })
        return contract

    def create_contract_assignment(self, data=None):
        data = data or {}
        defaults = {}
        defaults.update(data)
        if 'user' not in defaults:
            user = self.create_user()
        if 'contract' not in defaults:
            defaults['contract'] = self.create_project()
        defaults['start_date'] = defaults['contract'].start_date
        defaults['end_date'] = defaults['contract'].end_date
        return ContractAssignment.objects.create(**defaults)

    def log_time(self, delta=None, billable=True, project=None,
        start=None, end=None, status=None, pause=0, activity=None, user=None):
        if not user:
            user = self.user
        if delta and not end:
            hours, minutes = delta
        else:
            hours = 4
            minutes = 0
        if not start:
            start = timezone.now() - relativedelta(hour=0)
            #In case the default would fall off the end of the billing period
            if start.day >= 28:
                start -= relativedelta(days=1)
        if not end:
            end = start + datetime.timedelta(hours=hours, minutes=minutes)
        data = {'user': user,
                'start_time': start,
                'end_time': end,
                'seconds_paused': pause,
                }
        if project:
            data['project'] = project
        else:
            data['project'] = self.create_project(billable=billable)
        if activity:
            data['activity'] = activity
        else:
            if billable:
                data['activity'] = self.devl_activity
            else:
                data['activity'] = self.activity
        if status:
            data['status'] = status
        return self.create_entry(data)

    def create_user(self, username=None, email=None, password=None,
            user_permissions=None, groups=None, **kwargs):
        username = self.random_string(25) if not username else username
        email = self.random_string(10) + "@example.com" if not email else email
        password = self.random_string(25) if not password else password
        user = User.objects.create_user(username, email, password)
        if user_permissions:
            user.user_permissions = user_permissions
        if groups:
            user.groups = groups
        if kwargs:
            User.objects.filter(pk=user.pk).update(**kwargs)
        return User.objects.get(pk=user.pk)

    def create_auth_group(self, permissions=None, **kwargs):
        defaults = {
            'name': self.random_string(25),
        }
        defaults.update(kwargs)
        group = Group.objects.create(**defaults)
        if permissions:
            group.permissions = permissions
            group.save()
        return group

    def create_activity_group(self, name=None, data=None):
        data = data or {}
        defaults = {
            'name': name or self.random_string(25),
        }
        defaults.update(data)
        return ActivityGroup.objects.create(**defaults)

    def create_project_hours_entry(self, week_start=None, project=None,
                user=None, hours=None, **kwargs):
        week_start = week_start or utils.get_week_start(add_tzinfo=False)
        project = project or self.create_project()
        user = user or self.create_user()
        hours = Decimal(str(random.random() * 20)) if hours is None else hours
        return ProjectHours.objects.create(week_start=week_start,
                project=project, user=user, hours=hours, **kwargs)

    def setUp(self):
        self.user = self.create_user('user', 'u@abc.com', 'abc')
        self.user.last_name = 'Jones'
        self.user2 = self.create_user('user2', 'u2@abc.com', 'abc')
        self.user2.last_name = 'Smith'
        self.superuser = self.create_user('superuser', 'super@abc.com', 'abc',
                is_superuser=True)
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename__in=('can_clock_in', 'can_clock_out',
            'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
        self.user.save()
        self.user2.save()
        self.activity = Activity.objects.create(
            code="WRK",
            name="Work",
        )
        self.devl_activity = Activity.objects.create(
            code="devl",
            name="development",
            billable=True,
        )
        self.sick_activity = Activity.objects.create(
            code="sick",
            name="sick/personal",
            billable=False,
        )
        self.activity_group_all = ActivityGroup.objects.create(
            name='All',
        )
        self.activity_group_work = ActivityGroup.objects.create(
            name='Client work',
        )
        activities = Activity.objects.all()
        for activity in activities:
            activity.activity_group.add(self.activity_group_all)
            if activity != self.sick_activity:
                activity.activity_group.add(self.activity_group_work)
        self.business = Business.objects.create(
            name='Example Business',
            description='',
        )
        status = Attribute.objects.create(
            type='project-status',
            label='Current',
            enable_timetracking=True,
        )
        type_ = Attribute.objects.create(
            type='project-type',
            label='Web Sites',
            enable_timetracking=True,
        )
        self.project = Project.objects.create(
            name='Example Project 1',
            type=type_,
            status=status,
            business=self.business,
            point_person=self.user,
            activity_group=self.activity_group_work,
        )
        self.project2 = Project.objects.create(
            name='Example Project 2',
            type=type_,
            status=status,
            business=self.business,
            point_person=self.user2,
            activity_group=self.activity_group_all,
        )
        ProjectRelationship.objects.create(
            user=self.user,
            project=self.project,
        )
        self.location = self.create_location()
