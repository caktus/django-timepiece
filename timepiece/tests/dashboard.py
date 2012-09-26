import datetime
from decimal import Decimal

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

try:
    from django.utils import timezone
except ImportError:
    from timepiece import timezone

from timepiece.templatetags.timepiece_tags import get_active_hours
from timepiece.tests.base import TimepieceDataTestCase
from timepiece import utils


class DashboardTestCase(TimepieceDataTestCase):

    def setUp(self):
        super(DashboardTestCase, self).setUp()
        self.unpriveleged_user = User.objects.create_user(
            username='tester',
            password='abc',
            email='email@email.com'
        )
        self.url = reverse('timepiece-entries')
        self.text = [u'Clock In', u'Add Entry', u'My Active Entries']
        self.now = timezone.now()

    def test_unpriveleged_user(self):
        """
        A regular user should not be able to see what people are
        working on or timesheet related links
        """
        self.client.login(username='tester', password='abc')

        response = self.client.get(self.url)
        for text in self.text:
            self.assertNotContains(response, text)

    def test_timepiece_user(self):
        """
        A timepiece user should be able to see what others are
        working on as well as timesheet links
        """
        self.client.login(username='user', password='abc')

        response = self.client.get(self.url)
        for text in self.text:
            self.assertContains(response, text)

    def test_work_this_week(self):
        """
        Work This Week table should contain hours worked on projects this week,
        including from active entries.
        """
        projects = []
        projects.append(self.create_project(billable=True))
        projects.append(self.create_project(billable=False))
        past = []
        past.append(self.create_entry({  # 15 minutes
            'start_time': self.now + datetime.timedelta(minutes=5),
            'end_time': self.now + datetime.timedelta(minutes=20),
            'project': projects[0],
            'activity': self.create_activity(data={'billable': True}),
        }))
        past.append(self.create_entry({  # 15 minutes
            'start_time': self.now + datetime.timedelta(minutes=25),
            'end_time': self.now + datetime.timedelta(minutes=40),
            'project': projects[0],
            'activity': self.create_activity(data={'billable': True}),
        }))
        past.append(self.create_entry({  # 60 minutes
            'start_time': self.now + datetime.timedelta(minutes=45),
            'end_time': self.now + datetime.timedelta(minutes=105),
            'project': projects[1],
            'activity': self.create_activity(data={'billable': False}),
        }))
        current = self.create_entry({  # 30 minutes
            'start_time': self.now - datetime.timedelta(minutes=30),
            'project': projects[0],
            'activity': self.create_activity(data={'billable': True}),
        })
        current_hours = get_active_hours(current)
        total_hours = sum([p.hours for p in past]) + current_hours

        self.client.login(username='user', password='abc')
        response = self.client.get(self.url)
        context = response.context
        self.assertEquals(len(context['my_active_entries']), 1)
        self.assertEquals(get_active_hours(context['my_active_entries'][0]),
                current_hours)
        self.assertEquals(len(context['project_entries']), 2)
        for entry in context['project_entries']:
            if entry['project__pk'] == projects[0].pk:
                self.assertEquals(entry['sum'], Decimal('0.50'))
            else:
                self.assertEquals(entry['sum'], Decimal('1.00'))
        self.assertEquals(len(context['activity_entries']), 2)
        for entry in context['activity_entries']:
            self.assertEquals(entry['sum'], Decimal('1.00'))
        self.assertEquals(context['current_total'], total_hours)

    def test_time_detail(self):
        """
        An active entry should not appear in the Time
        Detail This Week table
        """
        entry = self.create_entry({
            'start_time': self.now,
            'end_time': self.now + datetime.timedelta(hours=1),
        })
        self.create_entry({
            'start_time': self.now + datetime.timedelta(hours=2),
            'project': self.create_project(billable=True)
        })

        self.client.login(username='user', password='abc')

        response = self.client.get(self.url)
        context = response.context
        self.assertEquals(len(context['this_weeks_entries']), 1)
        self.assertEquals(context['this_weeks_entries'][0], entry)
