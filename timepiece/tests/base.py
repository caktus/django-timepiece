import random
import urllib

from dateutil.relativedelta import relativedelta
from decimal import Decimal

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.auth import login, SESSION_KEY
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from django.utils import timezone

from timepiece.entries.models import Activity, Entry

from . import factories


class ViewTestMixin(object):
    """Utilities for testing views more easily."""
    url_name = ''  # Must be defined by implementing class.
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
            url = '{0}?{1}'.format(url, urllib.urlencode(get_kwargs, doseq=True))
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


class TimepieceDataTestCase(TestCase):

    def login_user(self, user, strict=True):
        """Log in a user without need for a password.

        Adapted from
        http://jameswestby.net/weblog/tech/17-directly-logging-in-a-user-in-django-tests.html
        """
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        engine = __import__(settings.SESSION_ENGINE, fromlist=['SessionStore'])

        # Create a fake request to store login details.
        request = HttpRequest()
        if self.client.session:
            request.session = self.client.session
        else:
            request.session = engine.SessionStore()
        login(request, user)

        # Set the cookie to represent the session.
        session_cookie = settings.SESSION_COOKIE_NAME
        self.client.cookies[session_cookie] = request.session.session_key
        cookie_data = {
            'max-age': None,
            'path': '/',
            'domain': settings.SESSION_COOKIE_DOMAIN,
            'secure': settings.SESSION_COOKIE_SECURE or None,
            'expires': None,
        }
        self.client.cookies[session_cookie].update(cookie_data)

        # Save the session values.
        request.session.save()

    def create_contract(self, projects=None, **kwargs):
        num_hours = kwargs.pop('num_hours', random.randint(10, 400))
        contract = factories.ProjectContractFactory.create(**kwargs)
        contract.projects.add(*(projects or []))
        # Create 2 ContractHour objects that add up to the hours we want
        for i in range(2):
            factories.ContractHourFactory.create(
                    hours=Decimal(str(num_hours/2.0)), contract=contract)
        return contract

    def log_time(self, delta=None, billable=True, project=None, start=None,
            end=None, status=None, pause=0, activity=None, user=None):
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
            end = start + relativedelta(hours=hours, minutes=minutes)
        data = {'user': user,
                'start_time': start,
                'end_time': end,
                'seconds_paused': pause,
                }
        if project:
            data['project'] = project
        else:
            data['project'] = factories.BillableProjectFactory.create()
        if activity:
            data['activity'] = activity
        else:
            if billable:
                data['activity'] = self.devl_activity
            else:
                data['activity'] = self.activity
        if status:
            data['status'] = status
        return factories.EntryFactory.create(**data)

    def setUp(self):
        self.user = factories.UserFactory.create()
        self.user2 = factories.UserFactory.create()
        self.superuser = factories.SuperuserFactory.create()
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename__in=('can_clock_in', 'can_clock_out',
            'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
        self.user.save()
        self.user2.save()
        self.activity = factories.ActivityFactory.create(code='WRK',
                name='Work')
        self.devl_activity = factories.ActivityFactory.create(code='devl',
                name='development', billable=True)
        self.sick_activity = factories.ActivityFactory.create(code="sick",
                name="sick/personal", billable=False)
        self.activity_group_all = factories.ActivityGroupFactory.create(
                name='All')
        self.activity_group_work = factories.ActivityGroupFactory.create(
                name='Client work')

        activities = Activity.objects.all()
        for activity in activities:
            activity.activity_group.add(self.activity_group_all)
            if activity != self.sick_activity:
                activity.activity_group.add(self.activity_group_work)
        self.business = factories.BusinessFactory.create()
        status = factories.StatusAttributeFactory.create(label='Current',
                enable_timetracking=True)
        type_ = factories.TypeAttributeFactory.create(label='Web Sites',
            enable_timetracking=True)
        self.project = factories.ProjectFactory.create(type=type_,
                status=status, business=self.business, point_person=self.user,
                activity_group=self.activity_group_work)
        self.project2 = factories.ProjectFactory.create(type=type_,
                status=status, business=self.business, point_person=self.user2,
                activity_group=self.activity_group_all)
        factories.ProjectRelationshipFactory.create(user=self.user,
                project=self.project)
        self.location = factories.LocationFactory.create()
