import datetime
import random
import string

from dateutil.relativedelta import relativedelta

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from timepiece import models as timepiece


class TimepieceDataTestCase(TestCase):
    def create_business(self, data={}):
        name = self.random_string(30, extra_chars=' ')
        defaults = {
            'name': name,
        }
        defaults.update(data)
        return timepiece.Business.objects.create(**defaults)

    def random_string(self, length=255, extra_chars=''):
        chars = string.letters + extra_chars
        return ''.join([random.choice(chars) for i in range(length)])

    def create_person(self, data={}):
        first_name = self.random_string(20)
        last_name = self.random_string(20)
        defaults = {
            'first_name': first_name,
            'last_name': last_name,
        }
        defaults.update(data)
        return User.objects.create(**defaults)

    def create_project_type(self, data={}):
        defaults = {
            'label': self.random_string(30, extra_chars=' '),
            'type': 'project-type',
        }
        defaults.update(data)
        return timepiece.Attribute.objects.create(**defaults)

    def create_project_status(self, data={}):
        defaults = {
            'label': self.random_string(24, extra_chars=' '),
            'type': 'project-status',
        }
        defaults.update(data)
        return timepiece.Attribute.objects.create(**defaults)

    def create_project(self, billable=False, name=None, data={}):
        if not name:
            name = self.random_string(30, extra_chars=' ')
        defaults = {
            'name': name,
            'type': self.create_project_type(data={'billable': billable}),
            'status': self.create_project_status(data={'billable': billable}),
        }
        defaults.update(data)
        if 'business' not in defaults:
            defaults['business'] = self.create_business()
        if 'point_person' not in defaults:
            defaults['point_person'] = User.objects.create_user(
                self.random_string(10),
                'test@example.com',
                'test',
            )
        return timepiece.Project.objects.create(**defaults)

    def create_project_relationship(self, data={}):
        defaults = {}
        defaults.update(data)
        if 'user' not in defaults:
            defaults['user'] = self.create_person()
        if 'project' not in defaults:
            defaults['project'] = self.create_project()
        return timepiece.ProjectRelationship.objects.create(**defaults)

    def create_activity(self, data={}):
        defaults = {
            'code': self.random_string(5, extra_chars=' '),
            'name': self.random_string(50, extra_chars=' '),
            'billable': False
        }
        defaults.update(data)
        return timepiece.Activity.objects.create(**defaults)

    def create_location(self, data={}):
        defaults = {
            'name': self.random_string(255, extra_chars=' '),
            'slug': self.random_string(255),
        }
        defaults.update(data)
        return timepiece.Location.objects.create(**defaults)

    def create_entry(self, data={}):
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
            defaults['status'] = 'unverified'
        return timepiece.Entry.objects.create(**defaults)

    def create_repeat_period(self, data={}):
        defaults = {
            'count': 1,
            'interval': 'month',
            'active': True,
        }
        defaults.update(data)
        return timepiece.RepeatPeriod.objects.create(**defaults)

    def create_person_repeat_period(self, data={}):
        defaults = {}
        defaults.update(data)
        if 'user' not in defaults:
            defaults['user'] = self.create_person()
        if 'repeat_period' not in defaults:
            defaults['repeat_period'] = self.create_repeat_period()
        return timepiece.PersonRepeatPeriod.objects.create(**defaults)

    def create_project_contract(self, data={}):
        defaults = {
            'start_date': datetime.date.today(),
            'end_date': datetime.date.today() + datetime.timedelta(weeks=2),
            'num_hours': random.randint(10, 400),
            'status': 'current',
        }
        defaults.update(data)
        if 'project' not in defaults:
            defaults['project'] = self.create_project()
        return timepiece.ProjectContract.objects.create(**defaults)

    def create_contract_assignment(self, data={}):
        defaults = {}
        defaults.update(data)
        if 'user' not in defaults:
            user = self.create_person()
        if 'contract' not in defaults:
            defaults['contract'] = self.create_project()
        defaults['start_date'] = defaults['contract'].start_date
        defaults['end_date'] = defaults['contract'].end_date
        return timepiece.ContractAssignment.objects.create(**defaults)

    def create_person_schedule(self, data={}):
        defaults = {
            'hours_per_week': 40,
            'end_date': datetime.date.today() + datetime.timedelta(weeks=2),
        }
        defaults.update(data)
        if 'user' not in defaults:
            defaults['user'] = self.create_person()
        return timepiece.PersonSchedule.objects.create(**defaults)

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
            start = datetime.datetime.now() - relativedelta(hour=0)
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

    def setUp(self):
        self.user = User.objects.create_user('user', 'u@abc.com', 'abc')
        self.user.last_name = 'Jones'
        self.user2 = User.objects.create_user('user2', 'u2@abc.com', 'abc')
        self.user2.last_name = 'Smith'
        self.superuser = User.objects.create_user('superuser',
                                                  'super@abc.com', 'abc')
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(timepiece.Entry),
            codename__in=('can_clock_in', 'can_clock_out',
            'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
        self.superuser.is_superuser = True
        self.superuser.save()
        self.user.save()
        self.user2.save()
        self.user = self.user
        self.activity = timepiece.Activity.objects.create(
            code="WRK",
            name="Work",
        )
        self.devl_activity = timepiece.Activity.objects.create(
            code="devl",
            name="development",
            billable=True,
        )
        self.sick_activity = timepiece.Activity.objects.create(
            code="sick",
            name="sick/personal",
            billable=False,
        )
        self.activity_group_all = timepiece.ActivityGroup.objects.create(
            name='All',
        )
        self.activity_group_work = timepiece.ActivityGroup.objects.create(
            name='Client work',
        )
        activities = timepiece.Activity.objects.all()
        for activity in activities:
            activity.activity_group.add(self.activity_group_all)
            if activity != self.sick_activity:
                activity.activity_group.add(self.activity_group_work)
        self.business = timepiece.Business.objects.create(
            name='Example Business',
            description='',
        )
        status = timepiece.Attribute.objects.create(
            type='project-status',
            label='Current',
            enable_timetracking=True,
        )
        type_ = timepiece.Attribute.objects.create(
            type='project-type',
            label='Web Sites',
            enable_timetracking=True,
        )
        self.project = timepiece.Project.objects.create(
            name='Example Project 1',
            type=type_,
            status=status,
            business=self.business,
            point_person=self.user,
            activity_group=self.activity_group_work,
        )
        self.project2 = timepiece.Project.objects.create(
            name='Example Project 2',
            type=type_,
            status=status,
            business=self.business,
            point_person=self.user2,
            activity_group=self.activity_group_all,
        )
        timepiece.ProjectRelationship.objects.create(
            user=self.user,
            project=self.project,
        )
        self.location = self.create_location()
