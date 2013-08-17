import json
import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

from timepiece import utils
from timepiece.tests.base import TimepieceDataTestCase
from timepiece.tests import factories
from timepiece.tests.base import ViewTestMixin

from timepiece.entries.models import Entry, ProjectHours
from timepiece.entries.views import ScheduleView


class ProjectHoursTestCase(ViewTestMixin, TimepieceDataTestCase):

    def setUp(self):
        self.user = factories.UserFactory.create()
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename__in=('can_clock_in', 'can_clock_out', 'can_pause',
                    'change_entry')
        )
        self.user.user_permissions = permissions
        self.user.save()
        self.superuser = factories.SuperuserFactory.create()

        self.tracked_status = factories.StatusAttributeFactory.create(
                label='Current', billable=True, enable_timetracking=True)
        self.untracked_status = factories.StatusAttributeFactory.create(
                label='Closed', billable=False, enable_timetracking=False)
        self.tracked_type = factories.TypeAttributeFactory.create(
                label='Tracked', billable=True, enable_timetracking=True)
        self.untracked_type = factories.TypeAttributeFactory.create(
                label='Untracked', billable=False, enable_timetracking=False)

        self.work_activities = factories.ActivityGroupFactory.create(name='Work')
        self.leave_activities = factories.ActivityGroupFactory.create(name='Leave')
        self.all_activities = factories.ActivityGroupFactory.create(name='All')

        self.leave_activity = factories.ActivityFactory.create(code='leave',
                name='Leave', billable=False)
        self.leave_activity.activity_group.add(self.leave_activities,
                self.all_activities)
        self.work_activity = factories.ActivityFactory.create(code='work',
                name='Work', billable=True)
        self.work_activity.activity_group.add(self.work_activities,
                self.all_activities)

        data = {
            'type': self.tracked_type,
            'status': self.tracked_status,
            'activity_group': self.work_activities,
        }
        self.tracked_project = factories.BillableProjectFactory.create(
                name='Tracked', **data)
        data = {
            'type': self.untracked_type,
            'status': self.untracked_status,
            'activity_group': self.all_activities,
        }
        self.untracked_project = factories.BillableProjectFactory.create(
                name='Untracked', **data)


class ProjectHoursModelTestCase(ProjectHoursTestCase):

    def test_week_start(self):
        """week_start should always save to Monday of the given week."""
        monday = datetime.date(2012, 07, 16)
        for i in range(7):
            date = monday + relativedelta(days=i)
            entry = ProjectHours.objects.create(
                    week_start=date, project=self.tracked_project,
                    user=self.user)
            self.assertEquals(entry.week_start.date(), monday)
            ProjectHours.objects.all().delete()


class ProjectHoursListViewTestCase(ProjectHoursTestCase):

    def setUp(self):
        super(ProjectHoursListViewTestCase, self).setUp()
        self.past_week = utils.get_week_start(datetime.date(2012, 4, 1)).date()
        self.current_week = utils.get_week_start().date()
        for i in range(5):
            factories.ProjectHoursFactory.create(week_start=self.past_week,
                    published=True)
            factories.ProjectHoursFactory.create(week_start=self.current_week,
                    published=True)
        self.url = reverse('view_schedule')
        self.login_user(self.user)
        self.date_format = '%Y-%m-%d'

    def test_no_permission(self):
        """User must have permission entries.can_clock_in to view page."""
        self.basic_user = factories.UserFactory.create()
        self.login_user(self.basic_user)
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 302)

    def test_permission(self):
        """User must have permission entries.can_clock_in to view page."""
        self.assertTrue(self.user.has_perm('entries.can_clock_in'))
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

        view = ScheduleView()
        all_entries = view.get_hours_for_week(self.past_week)
        users = response.context['users']
        projects = response.context['projects']
        count = 0

        for proj_id, name, entries in projects:
            for i in range(len(entries)):
                entry = entries[i]
                if entry:
                    count += 1
                    self.assertTrue(all_entries.filter(project__id=proj_id,
                            user__id=users[i][0],
                            hours=entry['hours']).exists())
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
        self.assertEquals(len(response.context['users']), 0)

    def test_all_users_for_project(self):
        """Each project should list hours for every user."""
        response = self.client.get(self.url)
        projects = response.context['projects']
        users = response.context['users']

        for proj_id, name, entries in projects:
            self.assertEquals(len(entries), len(users))


class ProjectHoursEditTestCase(ProjectHoursTestCase):
    def setUp(self):
        super(ProjectHoursEditTestCase, self).setUp()
        self.permission = Permission.objects.filter(
            codename='add_projecthours')
        self.manager = factories.UserFactory.create()
        self.manager.user_permissions = self.permission
        self.view_url = reverse('edit_schedule')
        self.ajax_url = reverse('ajax_schedule')
        self.week_start = utils.get_week_start(datetime.date.today())
        self.next_week = self.week_start + relativedelta(days=7)
        self.future = self.week_start + relativedelta(days=14)

    def create_project_hours(self):
        """Create project hours data"""
        ProjectHours.objects.create(
            week_start=self.week_start, project=self.tracked_project,
            user=self.user, hours="25.0")
        ProjectHours.objects.create(
            week_start=self.week_start, project=self.tracked_project,
            user=self.manager, hours="5.0")

        ProjectHours.objects.create(
            week_start=self.next_week, project=self.tracked_project,
            user=self.user, hours="15.0")
        ProjectHours.objects.create(
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
        self.login_user(self.manager)

        response = self.client.get(self.view_url)
        self.assertEquals(response.status_code, 200)

        response = self.client.get(self.ajax_url)
        self.assertEquals(response.status_code, 200)

    def test_no_permission_access(self):
        """
        If you are a regular user, edit view should redirect to regular view
        and you should not be able to request any ajax data.
        """
        self.login_user(self.user)

        response = self.client.get(self.view_url)
        self.assertEquals(response.status_code, 302)

        response = self.client.get(self.ajax_url)
        self.assertEquals(response.status_code, 302)

    def test_empty_ajax_call(self):
        """
        An ajax call should return empty data sets when project hours
        do not exist
        """
        self.login_user(self.manager)

        response = self.client.get(self.ajax_url)
        self.assertEquals(response.status_code, 200)

        data = json.loads(response.content)

        self.assertEquals(data['project_hours'], [])
        self.assertEquals(data['projects'], [])

    def test_users(self):
        """Should retrieve all users who can_clock_in."""
        perm = Permission.objects.get(codename='can_clock_in')
        group = factories.GroupFactory.create()
        group.permissions.add(perm)

        group_user = factories.UserFactory.create()
        group_user.groups.add(group)
        perm_user = self.user
        super_user = self.superuser

        self.login_user(self.manager)
        response = self.client.get(self.ajax_url)
        self.assertEquals(response.status_code, 200)
        users = [u['id'] for u in json.loads(response.content)['all_users']]
        self.assertEquals(len(users), 3)
        self.assertTrue(group_user.id in users)
        self.assertTrue(perm_user.id in users)
        self.assertTrue(super_user.id in users)

    def test_default_ajax_call(self):
        """
        An ajax call without any parameters should return the current
        weeks data
        """
        self.login_user(self.manager)
        self.create_project_hours()

        response = self.client.get(self.ajax_url)

        self.process_default_call(response)

    def test_default_empty_ajax_call(self):
        """
        An ajax call with the parameter present, but empty value, should
        return the same as a call with no parameter
        """
        self.login_user(self.manager)
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
        self.login_user(self.manager)
        self.create_project_hours()

        date = datetime.datetime.now() + relativedelta(days=7)
        response = self.client.get(self.ajax_url, data={
            'week_start': date.strftime('%Y-%m-%d')
        })
        self.assertEquals(response.status_code, 200)

        data = json.loads(response.content)

        self.assertEquals(len(data['project_hours']), 2)
        self.assertEquals(len(data['projects']), 1)
        correct_hours = {
            self.manager.id: 2.0,
            self.user.id: 15.0
        }
        for entry in data['project_hours']:
            self.assertEqual(entry['hours'], correct_hours[entry['user']])

    def test_ajax_create_successful(self):
        """
        A post request on the ajax url should create a new project
        hour entry and return the entry's pk
        """
        self.login_user(self.manager)

        self.assertEquals(ProjectHours.objects.count(), 0)

        data = {
            'hours': 5,
            'user': self.manager.pk,
            'project': self.tracked_project.pk,
            'week_start': self.week_start.strftime('%Y-%m-%d')
        }
        response = self.client.post(self.ajax_url, data=data)
        self.assertEquals(response.status_code, 200)

        ph = ProjectHours.objects.get()
        self.assertEquals(ProjectHours.objects.count(), 1)
        self.assertEquals(int(response.content), ph.pk)
        self.assertEquals(ph.hours, Decimal("5.0"))

    def test_ajax_create_unsuccessful(self):
        """
        If any of the data is missing, the server response should
        be a 500 error
        """
        self.login_user(self.manager)

        self.assertEquals(ProjectHours.objects.count(), 0)

        self.ajax_posts()

        self.assertEquals(ProjectHours.objects.count(), 0)

    def test_ajax_update_successful(self):
        """
        A put request to the url with the correct data should update
        an existing project hour entry
        """
        self.login_user(self.manager)

        ph = ProjectHours.objects.create(
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

        ph = ProjectHours.objects.get()
        self.assertEquals(ph.hours, Decimal("10"))

    def test_ajax_update_unsuccessful(self):
        """
        If the request to update is missing data, the server should respond
        with a 500 error
        """
        self.login_user(self.manager)

        ph = ProjectHours.objects.create(
            hours=Decimal('10.0'),
            project=self.untracked_project,
            user=self.manager
        )

        self.ajax_posts()

        self.assertEquals(ProjectHours.objects.count(), 1)
        self.assertEquals(ph.hours, Decimal('10.0'))

    def test_ajax_delete_successful(self):
        """
        A delete request with a valid pk should delete the project
        hours entry from the database
        """
        self.login_user(self.manager)

        ph = ProjectHours.objects.create(
            hours=Decimal('5.0'),
            project=self.tracked_project,
            user=self.manager
        )

        url = reverse('ajax_schedule_detail', args=(ph.pk,))

        response = self.client.delete(url)
        self.assertEquals(response.status_code, 200)

        self.assertEquals(ProjectHours.objects.count(), 0)

    def test_duplicate_successful(self):
        """
        You can copy hours from the previous week to the currently
        active week. A request with the duplicate key present will
        start the duplication process
        """
        self.login_user(self.manager)
        self.create_project_hours()

        msg = 'Project hours were copied'

        response = self.client.post(self.ajax_url, data={
            'week_update': self.future.strftime('%Y-%m-%d'),
            'duplicate': 'duplicate'
        }, follow=True)
        self.assertEquals(response.status_code, 200)

        messages = response.context['messages']
        self.assertEquals(messages._loaded_messages[0].message, msg)

        ph = ProjectHours.objects.all()
        self.assertEquals(ph.count(), 6)
        self.assertEquals(ph.filter(week_start__gte=self.future).count(), 2)

    def test_duplicate_unsuccessful_params(self):
        """
        Both week_update and duplicate must be present if hours
        duplication is to take place
        """
        self.login_user(self.manager)
        self.create_project_hours()

        response = self.client.post(self.ajax_url, data={
            'week_update': self.future.strftime('%Y-%m-%d')
        }, follow=True)
        self.assertEquals(response.status_code, 500)

        response = self.client.post(self.ajax_url, data={
            'duplicate': 'duplicate'
        }, follow=True)
        self.assertEquals(response.status_code, 500)

        self.assertEquals(ProjectHours.objects.count(), 4)

    def test_duplicate_dates(self):
        """
        If you specify a week and hours current exist for that week,
        the previous weeks hours will be copied over the current entries
        """
        self.login_user(self.manager)
        self.create_project_hours()

        msg = 'Project hours were copied'

        response = self.client.post(self.ajax_url, data={
            'week_update': self.next_week.strftime('%Y-%m-%d'),
            'duplicate': 'duplicate'
        }, follow=True)
        self.assertEquals(response.status_code, 200)

        messages = response.context['messages']
        self.assertEquals(messages._loaded_messages[0].message, msg)

        this_week_qs = ProjectHours.objects.filter(
            week_start=self.week_start
        ).values_list('hours', flat=True)
        next_week_qs = ProjectHours.objects.filter(
            week_start=self.next_week
        ).values_list('hours', flat=True)

        # ValueQuerySets do not like being compared...
        this_week_qs = list(this_week_qs)
        next_week_qs = list(next_week_qs)

        self.assertEquals(ProjectHours.objects.count(), 4)
        self.assertEquals(ProjectHours.objects.filter(
            published=False).count(), 4)
        self.assertEquals(this_week_qs, next_week_qs)

    def test_no_hours_to_copy(self):
        """
        You should be notified if there are no hours to copy
        from the previous week
        """
        self.login_user(self.manager)

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
        self.login_user(self.manager)
        self.create_project_hours()

        msg = 'Unpublished project hours are now published'

        ph = ProjectHours.objects.filter(published=True)
        self.assertEquals(ph.count(), 0)

        response = self.client.post(self.view_url, follow=True)
        self.assertEquals(response.status_code, 200)

        messages = response.context['messages']
        self.assertEquals(messages._loaded_messages[0].message, msg)

        ph = ProjectHours.objects.filter(published=True)
        self.assertEquals(ph.count(), 2)

        for p in ph:
            self.assertEquals(p.week_start, self.week_start.date())

    def test_publish_hours_unsuccessful(self):
        """
        If you post to the edit view and there are no hours to
        publish, you are told so
        """
        self.login_user(self.manager)
        self.create_project_hours()

        msg = 'There were no hours to publish'

        ProjectHours.objects.update(published=True)

        response = self.client.post(self.view_url, follow=True)
        self.assertEquals(response.status_code, 200)

        messages = response.context['messages']
        self.assertEquals(messages._loaded_messages[0].message, msg)

        ph = ProjectHours.objects.filter(published=True)
        self.assertEquals(ph.count(), 4)
