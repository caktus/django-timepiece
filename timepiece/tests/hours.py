import datetime

from dateutil.relativedelta import relativedelta

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

try:
    from django.utils import timezone
except ImportError:
    from timepiece import timezone

from timepiece import models as timepiece
from timepiece import utils
from timepiece.tests.base import TimepieceDataTestCase

class ProjectHoursTestCase(TimepieceDataTestCase):

    def setUp(self):
        self.user = self.create_user('user', 'u@abc.com', 'abc')
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(timepiece.Entry),
            codename__in=('can_clock_in', 'can_clock_out', 'can_pause',
                    'change_entry')
        )
        self.user.user_permissions = permissions
        self.user.save()
        self.superuser = self.create_user('super', 's@abc.com', 'abc', True)

        self.tracked_status = self.create_project_status(data={
                'label': 'Current', 'billable': True,
                'enable_timetracking': True})
        self.untracked_status = self.create_project_status(data={
                'label': 'Closed', 'billable': False,
                'enable_timetracking': False})
        self.tracked_type = self.create_project_type(data={
                'label': 'Tracked', 'billable': True,
                'enable_timetracking': True})
        self.untracked_type = self.create_project_type(data={
                'label': 'Untracked', 'billable': False,
                'enable_timetracking': False})

        self.work_activities = self.create_activity_group('Work')
        self.leave_activities = self.create_activity_group('Leave')
        self.all_activities = self.create_activity_group('All')

        self.leave_activity = self.create_activity(
            activity_groups=[self.leave_activities, self.all_activities],
            data={'code': 'leave', 'name': 'Leave', 'billable': False}
        )
        self.work_activity = self.create_activity(
            activity_groups=[self.work_activities, self.all_activities],
            data={'code': 'work', 'name': 'Work', 'billable': True}
        )

        data = {
            'type': self.tracked_type,
            'status': self.tracked_status,
            'activity_group': self.work_activities,
        }
        self.tracked_project = self.create_project(True, 'Tracked', data)
        data = {
            'type': self.untracked_type,
            'status': self.untracked_status,
            'activity_group': self.all_activities,
        }
        self.untracked_project = self.create_project(True, 'Untracked', data)


class ProjectHoursModelTestCase(ProjectHoursTestCase):

    def test_week_start(self):
        """week_start should always save to Monday of the given week."""
        monday = datetime.datetime(2012, 07, 16,
                tzinfo=timezone.get_current_timezone())
        for i in range(7):
            date = monday + relativedelta(days=i)
            entry = timepiece.ProjectHours.objects.create(
                week_start=date, project=self.tracked_project, user=self.user)
            self.assertEquals(entry.week_start, monday)


class ProjectHoursListViewTestCase(ProjectHoursTestCase):

    def setUp(self):
        super(ProjectHoursListViewTestCase, self).setUp()
        self.past_week = utils.get_week_start(datetime.datetime(2012, 4, 1))
        self.current_week = utils.get_week_start()
        for i in range(5):
            self.create_project_hours_entry(self.past_week)
            self.create_project_hours_entry(self.current_week)
        self.url = reverse('project_hours_list')
        self.client.login(username='user', password='abc')
        self.date_format = '%m/%d/%Y'

    def test_no_permission(self):
        """Permissions are required to view the page."""
        # TODO
        pass

    def test_permission(self):
        """Permissions are required to view the page."""
        # TODO
        pass

    def test_default_filter(self):
        """Page shows project hours entries from the current week."""
        data = {}
        response = self.client.get(self.url, data)
        self.assertEquals(response.context['week'], self.current_week)

    def test_week_filter(self):
        """Filter shows all entries from Monday to Sunday of specified week."""
        data = {
            'week_start': self.past_week.strftime(self.date_format),
            'submit': '',
        }
        response = self.client.get(self.url, data)
        self.assertEquals(response.context['week'], self.past_week)

        all_entries = utils.get_project_hours_for_week(self.past_week)
        people = response.context['people']
        projects = response.context['projects']
        count = 0
        for proj_id, name, entries in projects:
            for i in range(len(entries)):
                entry = entries[i]
                if entry:
                    count += 1
                    self.assertTrue(all_entries.filter(project__id=proj_id,
                            user__id=people[i][0], hours=entry).exists())
        self.assertEquals(count, all_entries.count())

    def test_week_filter_midweek(self):
        """Filter corrects mid-week date to Monday of specified week."""
        wednesday = datetime.date(2012, 7, 4)
        monday = utils.get_week_start(wednesday)
        data = {
            'week_start': wednesday.strftime(self.date_format),
            'submit': '',
        }
        response = self.client.get(self.url, data)
        self.assertEquals(response.context['week'], monday)

    def test_no_entries(self):
        date = utils.get_week_start(datetime.datetime(2012, 3, 15))
        data = {
            'week_start': date.strftime('%m/%d/%Y'),
            'submit': '',
        }
        response = self.client.get(self.url, data)
        self.assertEquals(len(response.context['projects']), 0)
        self.assertEquals(len(response.context['people']), 0)

    def test_all_people_for_project(self):
        """Each project should list hours for every person."""
        response = self.client.get(self.url)
        projects = response.context['projects']
        people = response.context['people']

        for proj_id, name, entries in projects:
            self.assertEquals(len(entries), len(people))
