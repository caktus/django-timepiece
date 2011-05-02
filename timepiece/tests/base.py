import datetime
import random
import string

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
            'label': self.random_string(30, extra_chars=' '),
            'type': 'project-status', 
        }
        defaults.update(data)
        return timepiece.Attribute.objects.create(**defaults)
    
    def create_project(self, data={}):
        name = self.random_string(30, extra_chars=' ')
        defaults = {
            'name': name,
            'type': self.create_project_type(),
            'status': self.create_project_status(),
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
        if 'activity' not in defaults:
            defaults['activity'] = self.create_activity()
        if 'project' not in defaults:
            defaults['project'] = self.create_project()
        if 'location' not in defaults:
            defaults['location'] = self.create_location()
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

    def setUp(self):
        self.user = User.objects.create_user('user', 'u@abc.com', 'abc')
        self.user2 = User.objects.create_user('user2', 'u2@abc.com', 'abc')
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(timepiece.Entry),
            codename__in=('can_clock_in', 'can_clock_out', 'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions

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
        )
        self.project = timepiece.Project.objects.create(
            name='Example Project 1',
            type=type_,
            status=status,
            business=self.business,
            point_person=self.user,
        )
        self.project2 = timepiece.Project.objects.create(
            name='Example Project 2',
            type=type_,
            status=status,
            business=self.business,
            point_person=self.user2,
        )
        timepiece.ProjectRelationship.objects.create(
            user=self.user,
            project=self.project,
        )
        self.location = self.create_location()
