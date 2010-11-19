from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from timepiece import models as timepiece
from crm import models as crm
from crm.tests import CrmDataTestCase


class TimepieceDataTestCase(CrmDataTestCase):
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
        if 'contact' not in defaults:
            defaults['contact'] = self.create_person()
        if 'project' not in defaults:
            defaults['project'] = self.create_project()
        return timepiece.ProjectRelationship.objects.create(**defaults)
    
    def create_activity(self, data={}):
        defaults = {
            'code': self.random_string(5, extra_chars=' '),
            'name': self.random_string(50, extra_chars=' '),
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
        if 'contact' not in defaults:
            defaults['contact'] = self.create_person()
        if 'repeat_period' not in defaults:
            defaults['repeat_period'] = self.create_repeat_period()
        return timepiece.PersonRepeatPeriod.objects.create(**defaults)
    
    def setUp(self):
        self.user = User.objects.create_user('user', 'u@abc.com', 'abc')
        self.user2 = User.objects.create_user('user2', 'u2@abc.com', 'abc')
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(timepiece.Entry),
            codename__in=('can_clock_in', 'can_clock_out', 'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
        self.contact = crm.Contact.objects.create(
            first_name='John',
            last_name='Doe',
            sort_name='doe-john',
            type='individual',
            user=self.user,
            description='',
        )
        self.activity = timepiece.Activity.objects.create(
            code="WRK",
            name="Work",
        )
        self.business = crm.Contact.objects.create(
            name='Example Business',
            slug='example-business',
            sort_name='example-business',
            type='business',
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
            contact=self.contact,
            project=self.project,
        )
        self.location = self.create_location()
