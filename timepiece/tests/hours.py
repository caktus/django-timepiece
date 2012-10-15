import json
import datetime
import urllib
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

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
        monday = datetime.date(2012, 07, 16)
        for i in range(7):
            date = monday + relativedelta(days=i)
            entry = timepiece.ProjectHours.objects.create(
                    week_start=date, project=self.tracked_project,
                    user=self.user)
            self.assertEquals(entry.week_start.date(), monday)
            timepiece.ProjectHours.objects.all().delete()


class ProjectHoursListViewTestCase(ProjectHoursTestCase):

    def setUp(self):
        super(ProjectHoursListViewTestCase, self).setUp()
        self.past_week = utils.get_week_start(datetime.date(2012, 4, 1)).date()
        self.current_week = utils.get_week_start().date()
        for i in range(5):
            self.create_project_hours_entry(self.past_week, published=True)
            self.create_project_hours_entry(self.current_week, published=True)
        self.url = reverse('project_hours')
        self.client.login(username='user', password='abc')
        self.date_format = '%Y-%m-%d'

    def test_no_permission(self):
        """User must have permission timepiece.can_clock_in to view page."""
        basic_user = self.create_user('basic', 'b@e.com', 'abc')
        self.client.login(username='basic', password='abc')
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 302)

    def test_permission(self):
        """User must have permission timepiece.can_clock_in to view page."""
        self.assertTrue(self.user.has_perm('timepiece.can_clock_in'))
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)

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
        self.assertEquals(response.context['week'].date(), self.past_week)

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
        monday = utils.get_week_start(wednesday).date()
        data = {
            'week_start': wednesday.strftime(self.date_format),
            'submit': '',
        }
        response = self.client.get(self.url, data)
        self.assertEquals(response.context['week'].date(), monday)

    def test_no_entries(self):
        date = utils.get_week_start(datetime.date(2012, 3, 15))
        data = {
            'week_start': date.strftime('%Y-%m-%d'),
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


class ProjectHoursEditTestCase(ProjectHoursTestCase):
    def setUp(self):
        super(ProjectHoursEditTestCase, self).setUp()
        self.permission = Permission.objects.filter(
            codename='add_projecthours')
        self.manager = self.create_user('manager', 'e@e.com', 'abc')
        self.manager.user_permissions = self.permission
        self.view_url = reverse('edit_project_hours')
        self.ajax_url = reverse('project_hours_ajax_view')
        self.week_start = utils.get_week_start(datetime.date.today())
        self.next_week = self.week_start + relativedelta(days=7)
        self.future = self.week_start + relativedelta(days=14)

    def create_project_hours(self):
        """Create project hours data"""
        timepiece.ProjectHours.objects.create(
            week_start=self.week_start, project=self.tracked_project,
            user=self.user, hours="25.0")
        timepiece.ProjectHours.objects.create(
            week_start=self.week_start, project=self.tracked_project,
            user=self.manager, hours="5.0")

        timepiece.ProjectHours.objects.create(
            week_start=self.next_week, project=self.tracked_project,
            user=self.user, hours="15.0")
        timepiece.ProjectHours.objects.create(
            week_start=self.next_week, project=self.tracked_project,
            user=self.manager, hours="2.0")

    def ajax_posts(self):
        date_msg = 'Parameter week_start must be a date in the format ' \
            'yyyy-mm-dd'
        msg = 'The request must contain values for user, project, and hours'

        response = self.client.post(self.ajax_url, data={
            'hours': 5,
            'week_start': '2012-07-23'
        })
        self.assertEquals(response.status_code, 500)
        self.assertEquals(response.content, msg)

        response = self.client.post(self.ajax_url, data={
            'hours': 5,
            'project': self.tracked_project.pk,
            'week_start': '2012-07-23'
        })
        self.assertEquals(response.status_code, 500)
        self.assertEquals(response.content, msg)

        response = self.client.post(self.ajax_url, data={
            'project': self.tracked_project.pk,
            'week_start': '2012-07-23'
        })
        self.assertEquals(response.status_code, 500)
        self.assertEquals(response.content, msg)

        response = self.client.post(self.ajax_url, data={
            'project': self.tracked_project.pk,
            'user': self.manager.pk,
            'week_start': '2012-07-23'
        })
        self.assertEquals(response.status_code, 500)
        self.assertEquals(response.content, msg)

        response = self.client.post(self.ajax_url, data={
            'user': self.manager.pk,
            'week_start': '2012-07-23'
        })
        self.assertEquals(response.status_code, 500)
        self.assertEquals(response.content, msg)

        response = self.client.post(self.ajax_url, data={
            'hours': 5,
            'user': self.manager.pk,
            'week_start': '2012-07-23'
        })
        self.assertEquals(response.status_code, 500)
        self.assertEquals(response.content, msg)

        response = self.client.post(self.ajax_url, data={
            'week_start': '2012-07-23'
        })
        self.assertEquals(response.status_code, 500)
        self.assertEquals(response.content, msg)

        response = self.client.post(self.ajax_url, data={
            'hours': 5,
            'user': self.manager.pk,
            'project': self.tracked_project.pk
        })
        self.assertEquals(response.status_code, 500)
        self.assertEquals(response.content, date_msg)

    def process_default_call(self, response):
        self.assertEquals(response.status_code, 200)

        data = json.loads(response.content)

        self.assertEquals(len(data['project_hours']), 2)
        self.assertEquals(len(data['projects']), 1)

        correct_hours = {self.manager.id: 5.0, self.user.id: 25.0}
        for entry in data['project_hours']:
            self.assertEquals(entry['hours'], correct_hours[entry['user']])

    def test_permission_access(self):
        """
        You must have the permission to view the edit page or
        the ajax page
        """
        self.client.login(username='manager', password='abc')

        response = self.client.get(self.view_url)
        self.assertEquals(response.status_code, 200)

        response = self.client.get(self.ajax_url)
        self.assertEquals(response.status_code, 200)

    def test_no_permission_access(self):
        """
        If you are a regular user, you shouldnt be able to view the edit page
        or request any ajax data
        """
        self.client.login(username='basic', password='abc')

        response = self.client.get(self.view_url)
        self.assertEquals(response.status_code, 302)

        response = self.client.get(self.ajax_url)
        self.assertEquals(response.status_code, 302)

    def test_empty_ajax_call(self):
        """
        An ajax call should return empty data sets when project hours
        do not exist
        """
        self.client.login(username='manager', password='abc')

        response = self.client.get(self.ajax_url)
        self.assertEquals(response.status_code, 200)

        data = json.loads(response.content)

        self.assertEquals(data['project_hours'], [])
        self.assertEquals(data['projects'], [])

    def test_default_ajax_call(self):
        """
        An ajax call without any parameters should return the current
        weeks data
        """
        self.client.login(username='manager', password='abc')
        self.create_project_hours()

        response = self.client.get(self.ajax_url)

        self.process_default_call(response)

    def test_default_empty_ajax_call(self):
        """
        An ajax call with the parameter present, but empty value, should
        return the same as a call with no parameter
        """
        self.client.login(username='manager', password='abc')
        self.create_project_hours()

        response = self.client.get(self.ajax_url, data={
            'week_start': ''
        })

        self.process_default_call(response)

    def test_ajax_call_date(self):
        """
        An ajax call with the 'week_of' parameter should return
        the data for that week
        """
        self.client.login(username='manager', password='abc')
        self.create_project_hours()

        date = datetime.datetime.now() + relativedelta(days=7)
        response = self.client.get(self.ajax_url, data={
            'week_start': date.strftime('%Y-%m-%d')
        })
        self.assertEquals(response.status_code, 200)

        data = json.loads(response.content)

        self.assertEquals(len(data['project_hours']), 2)
        self.assertEquals(len(data['projects']), 1)

        self.assertEquals(data['project_hours'][0]['hours'], 15.0)
        self.assertEquals(data['project_hours'][1]['hours'], 2.0)

    def test_ajax_create_successful(self):
        """
        A post request on the ajax url should create a new project
        hour entry and return the entry's pk
        """
        self.client.login(username='manager', password='abc')

        self.assertEquals(timepiece.ProjectHours.objects.count(), 0)

        data = {
            'hours': 5,
            'user': self.manager.pk,
            'project': self.tracked_project.pk,
            'week_start': self.week_start.strftime('%Y-%m-%d')
        }
        response = self.client.post(self.ajax_url, data=data)
        self.assertEquals(response.status_code, 200)

        ph = timepiece.ProjectHours.objects.get()
        self.assertEquals(timepiece.ProjectHours.objects.count(), 1)
        self.assertEquals(int(response.content), ph.pk)
        self.assertEquals(ph.hours, Decimal("5.0"))

    def test_ajax_create_unsuccessful(self):
        """
        If any of the data is missing, the server response should
        be a 500 error
        """
        self.client.login(username='manager', password='abc')

        self.assertEquals(timepiece.ProjectHours.objects.count(), 0)

        self.ajax_posts()

        self.assertEquals(timepiece.ProjectHours.objects.count(), 0)

    def test_ajax_update_successful(self):
        """
        A put request to the url with the correct data should update
        an existing project hour entry
        """
        self.client.login(username='manager', password='abc')

        ph = timepiece.ProjectHours.objects.create(
            hours=Decimal('5.0'),
            project=self.tracked_project,
            user=self.manager
        )

        response = self.client.post(self.ajax_url, data={
            'project': self.tracked_project.pk,
            'user': self.manager.pk,
            'hours': 10,
            'week_start': self.week_start.strftime('%Y-%m-%d')
        })
        self.assertEquals(response.status_code, 200)

        ph = timepiece.ProjectHours.objects.get()
        self.assertEquals(ph.hours, Decimal("10"))

    def test_ajax_update_unsuccessful(self):
        """
        If the request to update is missing data, the server should respond
        with a 500 error
        """
        self.client.login(username='manager', password='abc')

        ph = timepiece.ProjectHours.objects.create(
            hours=Decimal('10.0'),
            project=self.untracked_project,
            user=self.manager
        )

        self.ajax_posts()

        self.assertEquals(timepiece.ProjectHours.objects.count(), 1)
        self.assertEquals(ph.hours, Decimal('10.0'))

    def test_ajax_delete_successful(self):
        """
        A delete request with a valid pk should delete the project
        hours entry from the database
        """
        self.client.login(username='manager', password='abc')

        ph = timepiece.ProjectHours.objects.create(
            hours=Decimal('5.0'),
            project=self.tracked_project,
            user=self.manager
        )

        url = reverse('project_hours_detail_view', args=(ph.pk,))

        response = self.client.delete(url)
        self.assertEquals(response.status_code, 200)

        self.assertEquals(timepiece.ProjectHours.objects.count(), 0)

    def test_duplicate_successful(self):
        """
        You can copy hours from the previous week to the currently
        active week. A request with the duplicate key present will
        start the duplication process
        """
        self.client.login(username='manager', password='abc')
        self.create_project_hours()

        msg = 'Project hours were copied'

        response = self.client.post(self.ajax_url, data={
            'week_update': self.future.strftime('%Y-%m-%d'),
            'duplicate': 'duplicate'
        }, follow=True)
        self.assertEquals(response.status_code, 200)

        messages = response.context['messages']
        self.assertEquals(messages._loaded_messages[0].message, msg)

        ph = timepiece.ProjectHours.objects.all()
        self.assertEquals(ph.count(), 6)
        self.assertEquals(ph.filter(week_start__gte=self.future).count(), 2)

    def test_duplicate_unsuccessful_params(self):
        """
        Both week_update and duplicate must be present if hours
        duplication is to take place
        """
        self.client.login(username='manager', password='abc')
        self.create_project_hours()

        response = self.client.post(self.ajax_url, data={
            'week_update': self.future.strftime('%Y-%m-%d')
        }, follow=True)
        self.assertEquals(response.status_code, 500)

        response = self.client.post(self.ajax_url, data={
            'duplicate': 'duplicate'
        }, follow=True)
        self.assertEquals(response.status_code, 500)

        self.assertEquals(timepiece.ProjectHours.objects.count(), 4)

    def test_duplicate_dates(self):
        """
        If you specify a week and hours current exist for that week,
        the previous weeks hours will be copied over the current entries
        """
        self.client.login(username='manager', password='abc')
        self.create_project_hours()

        msg = 'Project hours were copied'

        response = self.client.post(self.ajax_url, data={
            'week_update': self.next_week.strftime('%Y-%m-%d'),
            'duplicate': 'duplicate'
        }, follow=True)
        self.assertEquals(response.status_code, 200)

        messages = response.context['messages']
        self.assertEquals(messages._loaded_messages[0].message, msg)

        this_week_qs = timepiece.ProjectHours.objects.filter(
            week_start=self.week_start
        ).values_list('hours', flat=True)
        next_week_qs = timepiece.ProjectHours.objects.filter(
            week_start=self.next_week
        ).values_list('hours', flat=True)

        # ValueQuerySets do not like being compared...
        this_week_qs = list(this_week_qs)
        next_week_qs = list(next_week_qs)

        self.assertEquals(timepiece.ProjectHours.objects.count(), 4)
        self.assertEquals(timepiece.ProjectHours.objects.filter(
            published=False).count(), 4)
        self.assertEquals(this_week_qs, next_week_qs)

    def test_no_hours_to_copy(self):
        """
        You should be notified if there are no hours to copy
        from the previous week
        """
        self.client.login(username='manager', password='abc')

        msg = 'There are no hours to copy'

        response = self.client.post(self.ajax_url, data={
            'week_update': self.week_start.strftime('%Y-%m-%d'),
            'duplicate': 'duplicate'
        }, follow=True)
        self.assertEquals(response.status_code, 200)

        messages = response.context['messages']
        self.assertEquals(messages._loaded_messages[0].message, msg)

    def test_publish_hours(self):
        """
        If you post to the edit view, you can publish the hours for
        the given week
        """
        self.client.login(username='manager', password='abc')
        self.create_project_hours()

        msg = 'Unpublished project hours are now published'

        ph = timepiece.ProjectHours.objects.filter(published=True)
        self.assertEquals(ph.count(), 0)

        response = self.client.post(self.view_url, follow=True)
        self.assertEquals(response.status_code, 200)

        messages = response.context['messages']
        self.assertEquals(messages._loaded_messages[0].message, msg)

        ph = timepiece.ProjectHours.objects.filter(published=True)
        self.assertEquals(ph.count(), 2)

        for p in ph:
            self.assertEquals(p.week_start, self.week_start.date())

    def test_publish_hours_unsuccessful(self):
        """
        If you post to the edit view and there are no hours to
        publish, you are told so
        """
        self.client.login(username='manager', password='abc')
        self.create_project_hours()

        msg = 'There were no hours to publish'

        timepiece.ProjectHours.objects.update(published=True)

        response = self.client.post(self.view_url, follow=True)
        self.assertEquals(response.status_code, 200)

        messages = response.context['messages']
        self.assertEquals(messages._loaded_messages[0].message, msg)

        ph = timepiece.ProjectHours.objects.filter(published=True)
        self.assertEquals(ph.count(), 4)
