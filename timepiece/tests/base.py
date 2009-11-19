from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from timepiece import models as timepiece
from crm import models as crm


class BaseTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('user', 'u@abc.com', 'abc')
        self.user2 = User.objects.create_user('user2', 'u2@abc.com', 'abc')
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(timepiece.Entry),
            codename__in=('can_clock_in', 'can_clock_out', 'can_pause')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
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
        self.project = timepiece.Project.objects.create(
            name='Example Project 2',
            type=type_,
            status=status,
            business=self.business,
            point_person=self.user2,
        )
