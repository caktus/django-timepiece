import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import random
from time import sleep

from six.moves.urllib.parse import urlencode

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.test import TestCase

from timepiece import utils
from timepiece.tests.base import ViewTestMixin, LogTimeMixin
from timepiece.tests import factories

from timepiece.crm.utils import grouped_totals
from timepiece.entries.models import Activity, Entry
from timepiece.entries.forms import ClockInForm


class EditableTest(TestCase):

    def setUp(self):
        super(EditableTest, self).setUp()
        self.user = factories.User()
        self.project = factories.Project(
            type__enable_timetracking=True, status__enable_timetracking=True)
        self.entry = factories.Entry(**{
            'user': self.user,
            'project': self.project,
            'start_time': timezone.now() - relativedelta(days=6),
            'end_time':  timezone.now() - relativedelta(days=6),
            'seconds_paused': 0,
            'status': Entry.VERIFIED,
        })
        self.entry2 = factories.Entry(**{
            'user': self.user,
            'project': self.project,
            'start_time': timezone.now() - relativedelta(days=2),
            'end_time':  timezone.now() - relativedelta(days=2),
            'seconds_paused': 0,
            'status': Entry.UNVERIFIED,
        })

    def testUnEditable(self):
        self.assertFalse(self.entry.is_editable)

    def testEditable(self):
        self.assertTrue(self.entry2.is_editable)


class MyLedgerTest(ViewTestMixin, LogTimeMixin, TestCase):

    def setUp(self):
        super(MyLedgerTest, self).setUp()
        self.user = factories.User()
        self.user2 = factories.User()
        self.superuser = factories.Superuser()
        self.devl_activity = factories.Activity(billable=True)
        self.activity = factories.Activity()
        self.url = reverse('view_user_timesheet', args=(self.user.pk,))

    def login_with_permissions(self):
        view_entry_summary = Permission.objects.get(
            codename='view_entry_summary')
        user = factories.User()
        user.user_permissions.add(view_entry_summary)
        user.save()
        self.login_user(user)

    def test_timesheet_view_permission(self):
        """A user with the correct permissions should see the menu"""
        self.login_with_permissions()
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)
        self.assertTrue('user' in response.context['year_month_form'].fields)

    def test_timesheet_view_no_permission(self):
        """A regular user should not see the user menu"""
        self.login_user(self.user)
        response = self.client.get(self.url)
        self.assertTrue(response.status_code, 200)
        self.assertFalse('user' in response.context['year_month_form'].fields)

    def testEmptyTimeSheet(self):
        self.login_user(self.user)
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(list(response.context['entries']), [])

    def testEmptyHourlySummary(self):
        self.login_user(self.user)
        now = timezone.now()
        empty_month = now + relativedelta(months=1)
        data = {
            'year': empty_month.year,
            'month': empty_month.month,
        }
        url = reverse('view_user_timesheet', args=[self.user.pk])
        response = self.client.get(url, data)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['grouped_totals'], '')

    def testNotMyLedger(self):
        self.login_user(self.user2)
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 403)

    def testNoLedger(self):
        self.login_user(self.user2)
        self.url = reverse('dashboard')
        try:
            self.client.get(self.url)
        except Exception as e:
            self.fail(e)

    def make_entries(self):
        self.p1 = factories.BillableProject(name='1')
        self.p2 = factories.NonbillableProject(name='2')
        self.p4 = factories.BillableProject(name='4')
        self.p3 = factories.NonbillableProject(name='1')
        days = [
            utils.add_timezone(datetime.datetime(2011, 1, 1)),
            utils.add_timezone(datetime.datetime(2011, 1, 28)),
            utils.add_timezone(datetime.datetime(2011, 1, 31)),
            utils.add_timezone(datetime.datetime(2011, 2, 1)),
            timezone.now(),
        ]
        self.log_time(project=self.p1, start=days[0], delta=(1, 0))
        self.log_time(project=self.p2, start=days[0], delta=(1, 0))
        self.log_time(project=self.p4, start=days[0], delta=(1, 0))
        self.log_time(project=self.p1, start=days[1], delta=(1, 0))
        self.log_time(project=self.p3, start=days[1], delta=(1, 0))
        self.log_time(project=self.p4, start=days[1], delta=(1, 0))
        self.log_time(project=self.p1, start=days[2], delta=(1, 0))
        self.log_time(project=self.p2, start=days[2], delta=(1, 0))
        self.log_time(project=self.p4, start=days[2], delta=(1, 0))
        self.log_time(project=self.p1, start=days[3], delta=(1, 0))
        self.log_time(project=self.p3, start=days[3], delta=(1, 0))
        self.log_time(project=self.p4, start=days[3], delta=(1, 0))
        self.log_time(project=self.p1, start=days[4], delta=(1, 0))
        self.log_time(project=self.p3, start=days[4], delta=(1, 0))
        self.log_time(project=self.p4, start=days[4], delta=(1, 0))

    def testCurrentTimeSheet(self):
        self.login_user(self.user)
        self.make_entries()
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)
        self.assertEqual(len(response.context['entries']), 3)
        self.assertEqual(response.context['summary']['total'], Decimal(3))

    def testOldTimeSheet(self):
        self.login_user(self.user)
        self.make_entries()
        data = {
            'month': 1,
            'year': 2011,
        }
        response = self.client.get(self.url, data)
        self.assertEquals(response.status_code, 200)
        self.assertEqual(len(response.context['entries']), 9)
        self.assertEqual(response.context['summary']['total'], Decimal(9))


class ClockInTest(ViewTestMixin, TestCase):

    def setUp(self):
        super(ClockInTest, self).setUp()
        self.user = factories.User()
        self.user2 = factories.User()
        self.superuser = factories.Superuser()
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename__in=('can_clock_in', 'can_clock_out',
                          'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
        self.user.save()
        self.user2.save()
        self.activity = factories.Activity(code='WRK', name='Work')
        self.devl_activity = factories.Activity(
            code='devl', name='development', billable=True)
        self.sick_activity = factories.Activity(
            code="sick", name="sick/personal", billable=False)
        self.activity_group_all = factories.ActivityGroup(name='All')
        self.activity_group_work = factories.ActivityGroup(name='Client work')
        activities = Activity.objects.all()
        for activity in activities:
            activity.activity_group.add(self.activity_group_all)
            if activity != self.sick_activity:
                activity.activity_group.add(self.activity_group_work)
        self.business = factories.Business()
        status = factories.StatusAttribute(
            label='Current', enable_timetracking=True)
        type_ = factories.TypeAttribute(
            label='Web Sites', enable_timetracking=True)
        self.project = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user, activity_group=self.activity_group_work)
        self.project2 = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user2, activity_group=self.activity_group_all)
        factories.ProjectRelationship(user=self.user, project=self.project)
        self.location = factories.Location()

        self.url = reverse('clock_in')
        self.now = timezone.now()
        self.ten_min_ago = self.now - relativedelta(minutes=10)
        self.clock_in_form = {
            'project': self.project.pk,
            'location': self.location.pk,
            'activity': self.devl_activity.pk,
            'start_time_0': self.ten_min_ago.strftime('%m/%d/%Y'),
            'start_time_1': self.ten_min_ago.strftime('%H:%M:%S'),
        }

    def testClockIn(self):
        """Test the simplest clock in scenario"""
        self.login_user(self.user)
        data = self.clock_in_form
        response = self.client.post(self.url, data, follow=True)
        # Clock in form submission leads to the dashboard page
        # with one active entry
        self.assertRedirects(response, reverse('dashboard'),
                             status_code=302, target_status_code=200)
        entries = Entry.objects.filter(
            end_time__isnull=True, user=self.user
        )
        self.assertEqual(entries.count(), 1)

    def testClockInAutoOut(self):
        """
        Clocking in during an active entry automatically clocks out the current
        entry one second before the new entry.
        """
        self.login_user(self.user)
        factories.Entry(user=self.user, start_time=self.ten_min_ago)
        data = self.clock_in_form
        data.update({
            'start_time_0': self.now.strftime('%m/%d/%Y'),
            'start_time_1': self.now.strftime('%H:%M:%S'),
        })
        self.client.post(self.url, data)
        entries = Entry.objects.all()
        # These clock in times do not overlap
        for entry in entries:
            if entry.is_overlapping():
                self.fail('Overlapping Times')
        # There is one closed entry and open current entry
        closed_entry = entries.get(end_time__isnull=False)
        current_entry = entries.get(end_time__isnull=True)
        # The current start time is one second after the closed entry's end time
        self.assertEqual(closed_entry.end_time + relativedelta(seconds=1),
                         current_entry.start_time)

    def testClockInManyActive(self):
        """
        There should never be more than one active entry. If this happens,
        a 500 error should be raised so that we are notified of the situation.
        """
        self.login_user(self.user)
        entry1 = factories.Entry(**{
            'user': self.user,
            'start_time': self.ten_min_ago,
        })
        entry2 = factories.Entry(**{
            'user': self.user,
            'start_time': self.now - relativedelta(minutes=20),
        })
        data = self.clock_in_form
        data.update({
            'start_time_0': self.now.strftime('%m/%d/%Y'),
            'start_time_1': self.now.strftime('%H:%M:%S'),
        })
        try:
            self.client.post(self.url, data)
        except utils.ActiveEntryError as e:
            self.assertEqual(str(e), "Only one active entry is allowed.")
        else:
            self.fail("Only one active entry should be allowed.")
        self.assertEqual(Entry.objects.count(), 2)
        self.assertEqual(Entry.objects.get(pk=entry1.pk), entry1)
        self.assertEqual(Entry.objects.get(pk=entry2.pk), entry2)

    def testClockInCurrentStatus(self):
        """Verify the status of the current entry shows what is expected"""
        self.login_user(self.user)
        entry1 = factories.Entry(**{
            'user': self.user,
            'start_time': self.ten_min_ago,
        })
        data = self.clock_in_form
        data.update({
            'start_time_0': self.now.strftime('%m/%d/%Y'),
            'start_time_1': self.now.strftime('%H:%M:%S'),
        })
        response = self.client.get(self.url, data)
        self.assertEqual(response.context['active'], entry1)

    def testClockInPause(self):
        """
        Test that the user can clock in while the current entry is paused.
        The current entry will be clocked out.
        """
        self.login_user(self.user)
        entry1 = factories.Entry(**{
            'user': self.user,
            'start_time': self.ten_min_ago,
        })
        e_id = Entry.objects.get(pk=entry1.id)
        e_id.pause()
        data = self.clock_in_form
        data.update({
            'start_time_0': self.now.strftime('%m/%d/%Y'),
            'start_time_1': self.now.strftime('%H:%M:%S'),
            'active_comment': 'test comment',
        })
        self.client.post(self.url, data, follow=True)
        # obtain entry1 now that it is closed. The hours should be recorded
        e_id = Entry.objects.get(pk=entry1.id)
        self.assertTrue(e_id.is_closed)
        self.assertTrue(e_id.hours)
        self.assertEqual(e_id.comments, 'test comment')

    def testPausedEntryReportsCorrectTime(self):
        """
        Account for progress of time when reporting a paused entry.
        """
        self.login_user(self.user)
        xtime = self.now
        entry1 = factories.Entry(**{
            'user': self.user,
            'start_time': xtime - relativedelta(seconds=1),
            'pause_time': xtime,
        })
        entry = Entry.objects.get(pk=entry1.id)
        self.assertEqual(entry.get_total_seconds(), 1)
        sleep(2)
        entry = Entry.objects.get(pk=entry1.id)
        self.assertEqual(entry.get_total_seconds(), 1)

    def testClockInBlock(self):
        """
        The user cannot clock in to a time that is already logged
        """
        self.login_user(self.user)
        entry1_data = {
            'user': self.user,
            'project': self.project,
            'activity': self.devl_activity,
            'start_time': self.ten_min_ago,
            'end_time': self.now,
        }
        entry1 = factories.Entry(**entry1_data)
        entry1_data.update({
            'st_str': self.ten_min_ago.strftime('%H:%M:%S'),
            'end_str': self.now.strftime('%H:%M:%S'),
        })
        blocked_start_time = entry1.start_time + relativedelta(minutes=5)
        data = self.clock_in_form
        data.update({
            'start_time_0': blocked_start_time.strftime('%m/%d/%Y'),
            'start_time_1': blocked_start_time.strftime('%H:%M:%S'),
        })
        # This clock in attempt should be blocked by entry1
        response = self.client.post(self.url, data)
        form = response.context['form']
        self.assertEquals(len(form.errors), 1, form.errors)
        self.assertTrue('__all__' in form.errors, form.errors.keys())

    def testClockInSameTime(self):
        """
        Test that the user cannot clock in with the same start time as the
        active entry
        """
        self.login_user(self.user)
        entry1_data = {
            'user': self.user,
            'start_time': self.now,
            'project': self.project,
            'activity': self.devl_activity,
        }
        entry1 = factories.Entry(**entry1_data)
        entry1_data.update({
            'st_str': self.now.strftime('%H:%M:%S')
        })
        data = self.clock_in_form
        data.update({
            'start_time_0': entry1.start_time.strftime('%m/%d/%Y'),
            'start_time_1': entry1.start_time.strftime('%H:%M:%S'),
        })
        # This clock in attempt should be blocked by entry1 (same start time)
        response = self.client.post(self.url, data)
        self.assertFormError(response, 'form', None,
                             'Please enter a valid start time')
        self.assertFormError(
            response, 'form', 'start_time',
            'The start time is on or before the current entry: ' +
            '%(project)s - %(activity)s starting at %(st_str)s' % entry1_data)

    def testClockInBeforeCurrent(self):
        """
        Test that the user cannot clock in with a start time before the active
        entry
        """
        self.login_user(self.user)
        entry1_data = {
            'user': self.user,
            'project': self.project,
            'activity': self.devl_activity,
            'start_time': self.ten_min_ago,
        }
        entry1 = factories.Entry(**entry1_data)
        entry1_data.update({
            'st_str': self.ten_min_ago.strftime('%H:%M:%S')
        })
        before_entry1 = entry1.start_time - relativedelta(minutes=5)
        data = self.clock_in_form
        data.update({
            'start_time_0': before_entry1.strftime('%m/%d/%Y'),
            'start_time_1': before_entry1.strftime('%H:%M:%S'),
        })
        # This clock in attempt should be blocked by entry1
        # (It is before the start time of the current entry)
        response = self.client.post(self.url, data)
        form = response.context['form']
        self.assertEquals(len(form.errors), 2, form.errors)
        self.assertTrue('start_time' in form.errors, form.errors.keys)
        self.assertTrue('__all__' in form.errors, form.errors.keys)

    def testClockInActiveTooLong(self):
        """
        Test that if the active entry is too long, the clock in form will
        invalidate
        """
        self.login_user(self.user)
        entry1 = factories.Entry(**{
            'user': self.user,
            'start_time': self.now - relativedelta(hours=13),
        })
        end_time = self.now - relativedelta(seconds=1)
        data = self.clock_in_form
        data.update({
            'start_time_0': self.now.strftime('%m/%d/%Y'),
            'start_time_1': self.now.strftime('%H:%M:%S'),
        })
        response = self.client.post(self.url, data)
        err_msg = 'Ending time exceeds starting time by 12 hours ' \
            'or more for {0} on {1} at {2} to {3} at {4}.'.format(
                entry1.project,
                entry1.start_time.strftime('%m/%d/%Y'),
                entry1.start_time.strftime('%H:%M:%S'),
                end_time.strftime('%m/%d/%Y'),
                end_time.strftime('%H:%M:%S')
            )
        self.assertFormError(response, 'form', None, err_msg)

    def test_clockin_error_active_entry(self):
        """
        If you have an active entry and clock in to another,
        you should not be clocked out of the current active entry
        if the clock in form contains errors
        """
        self.login_user(self.user)

        # Create a valid entry and follow the redirect to the homepage
        response = self.client.post(self.url, self.clock_in_form, follow=True)
        self.assertEquals(response.status_code, 200)
        self.assertTrue(response.context['messages'])

        data = self.clock_in_form
        data.update({'start_time_0': None})
        response = self.client.post(self.url, data)

        msg = 'Enter a valid date.'
        self.assertFormError(response, 'form', 'start_time', msg)

        active = Entry.objects.get()
        self.assertIsNone(active.end_time)

    def test_clockin_correct_active_entry(self):
        """
        If you clock in with an an active entry, that entry
        should be clocked out
        """
        self.login_user(self.user)

        # Create a valid entry and follow the redirect to the homepage
        response = self.client.post(self.url, self.clock_in_form, follow=True)
        self.assertEquals(response.status_code, 200)
        self.assertTrue(response.context['messages'])

        active = Entry.objects.get()

        data = self.clock_in_form
        start_time = self.now + relativedelta(seconds=10)
        data.update({
            'start_time_0': start_time.strftime('%m/%d/%Y'),
            'start_time_1': start_time.strftime('%H:%M:%S')
        })
        response = self.client.post(self.url, data)

        active = Entry.objects.get(pk=active.pk)
        self.assertIsNotNone(active.end_time)

    def testProjectListFiltered(self):
        self.login_user(self.user)
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)
        projects = list(response.context['form'].fields['project'].queryset)
        self.assertTrue(self.project in projects)
        self.assertFalse(self.project2 in projects)
        self.project.status.enable_timetracking = False
        self.project.status.save()
        response = self.client.get(self.url)
        projects = list(response.context['form'].fields['project'].queryset)
        self.assertTrue(self.project not in projects)

    def testClockInLogin(self):
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 302)
        self.login_user(self.user)
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)

    def testClockInUnauthorizedProject(self):
        self.login_user(self.user)
        data = self.clock_in_form
        data.update({'project': self.project2.id})
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        err_msg = 'Select a valid choice. That choice is not one of the ' + \
                  'available choices.'
        self.assertFormError(response, 'form', 'project', err_msg)

    def testClockInBadActivity(self):
        self.login_user(self.user)
        data = self.clock_in_form
        data.update({
            'project': self.project.id,
            'activity': self.sick_activity.id,
        })
        response = self.client.post(self.url, data)
        err_msg = 'sick/personal is not allowed for this project. Please '
        err_msg += 'choose among development, and Work'
        self.assertFormError(response, 'form', None, err_msg)

    def test_clock_in_active_comments(self):
        """
        Comments left from editing the current active entry should appear
        if you are clocking in
        """
        entry = factories.Entry(**{
            'user': self.user,
            'start_time': self.ten_min_ago
        })
        entry.comments = 'Some comments'
        entry.save()

        self.login_user(self.user)

        response = self.client.get(self.url)
        self.assertContains(response, 'Some comments')


class AutoActivityTest(ViewTestMixin, LogTimeMixin, TestCase):
    """Test the initial value chosen for activity on clock in form"""

    def setUp(self):
        super(AutoActivityTest, self).setUp()
        self.user = factories.User()
        self.user2 = factories.User()
        self.superuser = factories.Superuser()
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename__in=('can_clock_in', 'can_clock_out',
                          'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
        self.user.save()
        self.user2.save()
        self.activity = factories.Activity(code='WRK', name='Work')
        self.devl_activity = factories.Activity(
            code='devl', name='development', billable=True)
        self.sick_activity = factories.Activity(
            code="sick", name="sick/personal", billable=False)
        self.activity_group_all = factories.ActivityGroup(name='All')
        self.activity_group_work = factories.ActivityGroup(name='Client work')

        activities = Activity.objects.all()
        for activity in activities:
            activity.activity_group.add(self.activity_group_all)
            if activity != self.sick_activity:
                activity.activity_group.add(self.activity_group_work)
        self.business = factories.Business()
        status = factories.StatusAttribute(
            label='Current', enable_timetracking=True)
        type_ = factories.TypeAttribute(
            label='Web Sites', enable_timetracking=True)
        self.project = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user, activity_group=self.activity_group_work)
        self.project2 = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user2, activity_group=self.activity_group_all)
        factories.ProjectRelationship(user=self.user, project=self.project)
        self.location = factories.Location()

    def get_activity(self, project=None):
        if not project:
            project = self.project
        initial = {'project': project.id}
        form = ClockInForm(user=self.user, initial=initial)
        return form.initial['activity']

    def testNewWorker(self):
        """The worker has 0 entries on this project. Activity should = None"""
        self.login_user(self.user)
        self.assertEqual(self.get_activity(), None)

    def testLastWorkedOneEntry(self):
        """The worker has one previous entry on the project"""
        self.login_user(self.user)
        self.log_time(project=self.project, activity=self.devl_activity)
        self.assertEqual(self.get_activity(), self.devl_activity.id)

    def testLastWorkedSeveralEntries(self):
        """The worker has several entries on a project. Use the most recent"""
        self.login_user(self.user)
        for day in range(0, 10):
            this_day = utils.add_timezone(datetime.datetime(2011, 1, 1))
            this_day += relativedelta(days=day)
            activity = self.activity if day == 9 else self.devl_activity
            self.log_time(start=this_day, project=self.project,
                          activity=activity)
        self.assertEqual(self.get_activity(), self.activity.id)

    def testLastWorkedSeveralProjects(self):
        """
        Obtain activities contingent on the project when worker is on several
        """
        self.login_user(self.user)
        project1 = self.project
        project2 = self.project2
        for day in range(0, 10):
            this_day = utils.add_timezone(datetime.datetime(2011, 1, 1))
            this_day += relativedelta(days=day)
            # Cycle through projects and activities
            project = project1 if day % 2 == 0 else project2
            activity = self.devl_activity if day % 3 == 0 else self.activity
            self.log_time(start=this_day, project=project, activity=activity)
        self.assertEqual(self.get_activity(project1), self.activity.id)
        self.assertEqual(self.get_activity(project2), self.devl_activity.id)


class ClockOutTest(ViewTestMixin, TestCase):

    def setUp(self):
        super(ClockOutTest, self).setUp()
        self.user = factories.User()
        self.user2 = factories.User()
        self.superuser = factories.Superuser()
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename__in=('can_clock_in', 'can_clock_out',
                          'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
        self.user.save()
        self.user2.save()
        self.activity = factories.Activity(code='WRK', name='Work')
        self.devl_activity = factories.Activity(
            code='devl', name='development', billable=True)
        self.sick_activity = factories.Activity(
            code="sick", name="sick/personal", billable=False)
        self.activity_group_all = factories.ActivityGroup(name='All')
        self.activity_group_work = factories.ActivityGroup(name='Client work')

        activities = Activity.objects.all()
        for activity in activities:
            activity.activity_group.add(self.activity_group_all)
            if activity != self.sick_activity:
                activity.activity_group.add(self.activity_group_work)
        self.business = factories.Business()
        status = factories.StatusAttribute(
            label='Current', enable_timetracking=True)
        type_ = factories.TypeAttribute(
            label='Web Sites', enable_timetracking=True)
        self.project = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user, activity_group=self.activity_group_work)
        self.project2 = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user2, activity_group=self.activity_group_all)
        factories.ProjectRelationship(user=self.user, project=self.project)
        self.location = factories.Location()

        self.url = reverse('clock_out')
        self.login_user(self.user)

        # Create an active entry, so that clock out tests don't have to.
        self.default_end_time = timezone.now()
        back = timezone.now() - relativedelta(hours=5)
        self.entry = factories.Entry(**{
            'user': self.user,
            'start_time': back,
            'project': self.project,
            'activity': self.devl_activity,
        })

    def testBasicClockOut(self):
        data = {
            'start_time_0': self.entry.start_time.strftime('%m/%d/%Y'),
            'start_time_1': self.entry.start_time.strftime('%H:%M:%S'),
            'end_time_0': self.default_end_time.strftime('%m/%d/%Y'),
            'end_time_1': self.default_end_time.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        self.client.post(self.url, data, follow=True)
        closed_entry = Entry.objects.get(pk=self.entry.pk)
        self.assertTrue(closed_entry.is_closed)

    def testClockOutWithSecondsPaused(self):
        """
        Test that clocking out of an unpaused entry with previous pause time
        calculates the correct amount of unpaused time.
        """
        entry_with_pause = self.entry
        # paused for a total of 1 hour
        entry_with_pause.seconds_paused = 3600
        entry_with_pause.save()
        data = {
            'start_time_0': entry_with_pause.start_time.strftime('%m/%d/%Y'),
            'start_time_1': entry_with_pause.start_time.strftime('%H:%M:%S'),
            'end_time_0': self.default_end_time.strftime('%m/%d/%Y'),
            'end_time_1': self.default_end_time.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        self.client.post(reverse('clock_out'), data)
        entry_with_pause = Entry.objects.get(pk=entry_with_pause.pk)
        self.assertAlmostEqual(entry_with_pause.hours, 4)

    def testClockOutWhilePaused(self):
        """
        Test that clocking out of a paused entry calculates the correct time
        """
        paused_entry = self.entry
        paused_entry.pause_time = self.entry.start_time \
            + relativedelta(hours=1)
        paused_entry.save()
        data = {
            'start_time_0': paused_entry.start_time.strftime('%m/%d/%Y'),
            'start_time_1': paused_entry.start_time.strftime('%H:%M:%S'),
            'end_time_0': self.default_end_time.strftime('%m/%d/%Y'),
            'end_time_1': self.default_end_time.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        self.client.post(reverse('clock_out'), data)
        paused_entry = Entry.objects.get(pk=paused_entry.pk)
        self.assertAlmostEqual(paused_entry.hours, 1, places=2)

    def testClockOutReverse(self):
        """
        Test that the user can't clock out at a time prior to the starting time
        """
        backward_entry = self.entry
        backward_entry.save()
        # reverse the times
        data = {
            'start_time_0': self.default_end_time.strftime('%m/%d/%Y'),
            'start_time_1': self.default_end_time.strftime('%H:%M:%S'),
            'end_time_0': self.entry.start_time.strftime('%m/%d/%Y'),
            'end_time_1': self.entry.start_time.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        response = self.client.post(reverse('clock_out'), data)
        self.assertFormError(response, 'form', None,
                             'Ending time must exceed the starting time')

    def testClockOutTooLong(self):
        end_time = self.entry.start_time + relativedelta(hours=13)
        data = {
            'start_time_0': self.entry.start_time.strftime('%m/%d/%Y'),
            'start_time_1': self.entry.start_time.strftime('%H:%M:%S'),
            'end_time_0': end_time.strftime('%m/%d/%Y'),
            'end_time_1': end_time.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        response = self.client.post(self.url, data)
        err_msg = 'Ending time exceeds starting time by 12 hours ' \
            'or more for {0} on {1} at {2} to {3} at {4}.'.format(
                self.entry.project,
                self.entry.start_time.strftime('%m/%d/%Y'),
                self.entry.start_time.strftime('%H:%M:%S'),
                end_time.strftime('%m/%d/%Y'),
                end_time.strftime('%H:%M:%S')
            )
        self.assertFormError(response, 'form', None, err_msg)

    def testClockOutPauseTooLong(self):
        paused_entry = self.entry
        paused_entry.seconds_paused = 60 * 60 * 13
        paused_entry.save()
        data = {
            'start_time_0': paused_entry.start_time.strftime('%m/%d/%Y'),
            'start_time_1': paused_entry.start_time.strftime('%H:%M:%S'),
            'end_time_0': self.default_end_time.strftime('%m/%d/%Y'),
            'end_time_1': self.default_end_time.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        response = self.client.post(reverse('clock_out'), data)
        err_msg = 'Ending time exceeds starting time by 12 hours ' \
            'or more for {0} on {1} at {2} to {3} at {4}.'.format(
                self.entry.project,
                paused_entry.start_time.strftime('%m/%d/%Y'),
                paused_entry.start_time.strftime('%H:%M:%S'),
                self.default_end_time.strftime('%m/%d/%Y'),
                self.default_end_time.strftime('%H:%M:%S')
            )
        self.assertFormError(response, 'form', None, err_msg)

    def testClockOutOverlap(self):
        """
        Test that the user cannot clock out if the times overlap with an
        existing entry
        """
        # Create a closed and valid entry
        now = timezone.now() - relativedelta(hours=5)
        entry1_data = {
            'user': self.user,
            'project': self.project,
            'activity': self.devl_activity,
            'start_time': now,
            'end_time': self.default_end_time
        }
        entry1 = factories.Entry(**entry1_data)
        entry1_data.update({
            'st_str': entry1.start_time.strftime('%H:%M:%S'),
            'end_str': entry1.end_time.strftime('%H:%M:%S'),
        })

        # Create a form with times that overlap with entry1
        bad_start = entry1.start_time - relativedelta(hours=1)
        bad_end = entry1.end_time + relativedelta(hours=1)
        factories.Entry(user=self.user, start_time=bad_start, end_time=bad_end)
        data = {
            'start_time_0': bad_start.strftime('%m/%d/%Y'),
            'start_time_1': bad_start.strftime('%H:%M:%S'),
            'end_time_0': bad_end.strftime('%m/%d/%Y'),
            'end_time_1': bad_end.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        # With entry1 on either side, a post with the bad_entry data should
        # fail
        response = self.client.post(reverse('clock_out'), data)
        form = response.context['form']
        self.assertEquals(len(form.errors), 1, form.errors.keys)
        self.assertTrue('__all__' in form.errors, form.errors)

    def test_clocking_out_inactive(self):
        # If clock out when not active, redirect to dashboard
        # (e.g. double-clicked clock out button or clicked it on an old page)

        # setUp clocked us in, so clock out again
        data = {
            'start_time_0': self.entry.start_time.strftime('%m/%d/%Y'),
            'start_time_1': self.entry.start_time.strftime('%H:%M:%S'),
            'end_time_0': self.default_end_time.strftime('%m/%d/%Y'),
            'end_time_1': self.default_end_time.strftime('%H:%M:%S'),
            'location': self.location.pk,
            }
        response = self.client.post(
            self.url, data,
            follow=True,
            )
        # Do it again - make sure we redirect to the dashboard
        response = self.client.post(
            self.url, data,
            follow=False,
            )
        self.assertRedirects(response, reverse('dashboard'),
                             status_code=302, target_status_code=200)


class CheckOverlap(ViewTestMixin, LogTimeMixin, TestCase):
    """
    With entry overlaps, entry.check_overlap method should return True
    With valid entries, check_overlap should return False
    """

    def setUp(self):
        super(CheckOverlap, self).setUp()

        self.user = factories.User()
        self.user2 = factories.User()
        self.superuser = factories.Superuser()
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename__in=('can_clock_in', 'can_clock_out',
                          'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
        self.user.save()
        self.user2.save()
        self.activity = factories.Activity(
            code='WRK', name='Work')
        self.devl_activity = factories.Activity(
            code='devl', name='development', billable=True)
        self.sick_activity = factories.Activity(
            code="sick", name="sick/personal", billable=False)
        self.activity_group_all = factories.ActivityGroup(name='All')
        self.activity_group_work = factories.ActivityGroup(name='Client work')

        activities = Activity.objects.all()
        for activity in activities:
            activity.activity_group.add(self.activity_group_all)
            if activity != self.sick_activity:
                activity.activity_group.add(self.activity_group_work)
        self.business = factories.Business()
        status = factories.StatusAttribute(
            label='Current', enable_timetracking=True)
        type_ = factories.TypeAttribute(
            label='Web Sites', enable_timetracking=True)
        self.project = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user, activity_group=self.activity_group_work)
        self.project2 = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user2, activity_group=self.activity_group_all)
        factories.ProjectRelationship(user=self.user, project=self.project)
        self.location = factories.Location()

        self.login_user(self.user)
        self.now = timezone.now()
        # define start and end times to create valid entries
        self.start = self.now - relativedelta(days=0, hours=8)
        self.end = self.now - relativedelta(days=0)
        # Create a valid entry for the tests to overlap with
        self.log_time(start=self.start, end=self.end)
        # define bad start times relative to the valid one (just in/outside)
        self.start_before = self.start - relativedelta(minutes=2)
        self.start_inside = self.start + relativedelta(minutes=2)
        self.end_inside = self.end - relativedelta(minutes=2)
        self.end_after = self.end + relativedelta(minutes=2)

    # helper functions
    def use_checkoverlap(self, entries):
        """
        Uses entry.check_overlap given a list of entries returns all overlaps
        """
        user_total_overlaps = 0
        for index_a, entry_a in enumerate(entries):
            for index_b in range(index_a, len(entries)):
                entry_b = entries[index_b]
                if entry_a.check_overlap(entry_b):
                    user_total_overlaps += 1
        return user_total_overlaps

    def get_entries(self):
        return Entry.objects.filter(user=self.user)

    # Invalid entries to test against
    def testBeforeAndIn(self):
        self.log_time(start=self.start_before, end=self.end_inside)
        user_total_overlaps = self.use_checkoverlap(self.get_entries())
        self.assertEqual(user_total_overlaps, 1)

    def testAfterAndIn(self):
        self.log_time(start=self.start_inside, end=self.end_after)
        user_total_overlaps = self.use_checkoverlap(self.get_entries())
        self.assertEqual(user_total_overlaps, 1)

    def testInside(self):
        self.log_time(start=self.start_inside, end=self.end_inside)
        user_total_overlaps = self.use_checkoverlap(self.get_entries())
        self.assertEqual(user_total_overlaps, 1)

    def testOutside(self):
        self.log_time(start=self.start_before, end=self.end_after)
        user_total_overlaps = self.use_checkoverlap(self.get_entries())
        self.assertEqual(user_total_overlaps, 1)

    def testOverlapWithPause(self):
        """Overlaps by two minutes. Passes because it has 2 min. of pause"""
        self.log_time(start=self.start_before, end=self.start_inside,
                      pause=120)
        user_total_overlaps = self.use_checkoverlap(self.get_entries())
        self.assertEqual(user_total_overlaps, 0)

    def testOverlapWithoutEnoughPause(self):
        """Overlaps by two minutes, but only has 119 seconds of pause"""
        self.log_time(start=self.start_before, end=self.start_inside,
                      pause=119)
        user_total_overlaps = self.use_checkoverlap(self.get_entries())
        self.assertEqual(user_total_overlaps, 1)


class CreateEditEntry(ViewTestMixin, TestCase):

    def setUp(self):
        super(CreateEditEntry, self).setUp()

        self.user = factories.User()
        self.user2 = factories.User()
        self.superuser = factories.Superuser()
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename__in=('can_clock_in', 'can_clock_out',
                          'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
        self.user.save()
        self.user2.save()
        self.activity = factories.Activity(code='WRK', name='Work')
        self.devl_activity = factories.Activity(
            code='devl', name='development', billable=True)
        self.sick_activity = factories.Activity(
            code="sick", name="sick/personal", billable=False)
        self.activity_group_all = factories.ActivityGroup(name='All')
        self.activity_group_work = factories.ActivityGroup(name='Client work')

        activities = Activity.objects.all()
        for activity in activities:
            activity.activity_group.add(self.activity_group_all)
            if activity != self.sick_activity:
                activity.activity_group.add(self.activity_group_work)
        self.business = factories.Business()
        status = factories.StatusAttribute(
            label='Current', enable_timetracking=True)
        type_ = factories.TypeAttribute(
            label='Web Sites', enable_timetracking=True)
        self.project = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user, activity_group=self.activity_group_work)
        self.project2 = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user2, activity_group=self.activity_group_all)
        factories.ProjectRelationship(user=self.user, project=self.project)
        self.location = factories.Location()

        self.login_user(self.user)
        self.now = timezone.now()
        valid_start = self.now - relativedelta(days=1)
        valid_end = valid_start + relativedelta(hours=1)
        self.ten_min_ago = self.now - relativedelta(minutes=10)
        self.two_hour_ago = self.now - relativedelta(hours=2)
        self.one_hour_ago = self.now - relativedelta(hours=1)
        # establish data, entries, urls for all tests
        self.default_data = {
            'project': self.project.pk,
            'location': self.location.pk,
            'activity': self.devl_activity.pk,
            'seconds_paused': 0,
            'start_time_0': valid_start.strftime('%m/%d/%Y'),
            'start_time_1': valid_start.strftime('%H:%M:%S'),
            'end_time_0': valid_end.strftime('%m/%d/%Y'),
            'end_time_1': valid_end.strftime('%H:%M:%S'),
        }
        self.closed_entry_data = {
            'user': self.user,
            'project': self.project,
            'activity': self.devl_activity,
            'start_time': self.two_hour_ago,
            'end_time': self.one_hour_ago,
        }
        self.current_entry_data = {
            'user': self.user,
            'project': self.project,
            'activity': self.devl_activity,
            'start_time': self.ten_min_ago,
        }
        self.closed_entry = factories.Entry(**self.closed_entry_data)
        self.current_entry = factories.Entry(**self.current_entry_data)
        self.closed_entry_data.update({
            'st_str': self.two_hour_ago.strftime('%H:%M:%S'),
            'end_str': self.one_hour_ago.strftime('%H:%M:%S'),
        })
        self.current_entry_data.update({
            'st_str': self.ten_min_ago.strftime('%H:%M:%S'),
        })
        self.create_url = reverse('create_entry')
        self.edit_closed_url = reverse('edit_entry', args=[self.closed_entry.pk])
        self.edit_current_url = reverse('edit_entry', args=[self.current_entry.pk])

    def testCreateEntry(self):
        """
        Test the ability to create a valid new entry
        """
        response = self.client.post(self.create_url, self.default_data,
                                    follow=True)
        self.assertRedirects(response, reverse('dashboard'),
                             status_code=302, target_status_code=200)
        self.assertContains(
            response, 'The entry has been created successfully', count=1)

    def testEditClosed(self):
        """
        Test the ability to edit a closed entry, using valid values
        """
        response = self.client.post(self.edit_closed_url, self.default_data,
                                    follow=True)
        self.assertRedirects(response, reverse('dashboard'),
                             status_code=302, target_status_code=200)
        self.assertContains(
            response, 'The entry has been updated successfully', count=1)

    def testEditCurrentSameTime(self):
        """
        Test the ability to edit a current entry, not changing the values
        """
        data = self.default_data
        data.update({
            'start_time_0': self.current_entry_data['start_time'].strftime(
                '%m/%d/%Y'),
            'start_time_1': self.current_entry_data['start_time'].strftime(
                '%H:%M:%S'),
        })
        response = self.client.post(self.edit_current_url, data, follow=True)
        # This post should redirect to the dashboard, with the correct message
        # and 1 active entry, because we updated the current entry from setUp
        self.assertRedirects(response, reverse('dashboard'),
                             status_code=302, target_status_code=200)
        self.assertContains(
            response, 'The entry has been updated successfully', count=1)
        entries = Entry.objects.filter(
            user=self.user, end_time__isnull=True)
        self.assertEquals(entries.count(), 1)

    def testEditCurrentDiffTime(self):
        """
        Test the ability to edit a current entry, using valid new values
        """
        data = self.default_data
        new_start = self.current_entry_data['start_time'] + \
            relativedelta(minutes=5)
        data.update({
            'start_time_0': new_start.strftime('%m/%d/%Y'),
            'start_time_1': new_start.strftime('%H:%M:%S'),
        })
        response = self.client.post(self.edit_current_url, data, follow=True)
        # This post should redirect to the dashboard, with the correct message
        # and 1 active entry, because we updated the current entry from setUp
        self.assertRedirects(response, reverse('dashboard'),
                             status_code=302, target_status_code=200)
        entries = Entry.objects.filter(user=self.user, end_time__isnull=True)
        self.assertEquals(entries.count(), 1)

    def testCreateBlockByClosed(self):
        """
        Test that the entry is blocked by closed entries that overlap
        """
        overlap_entry = self.default_data
        overlap_entry.update({
            'start_time_0': self.closed_entry.start_time.strftime('%m/%d/%Y'),
            'start_time_1': self.closed_entry.start_time.strftime('%H:%M:%S'),
            'end_time_0': self.closed_entry.end_time.strftime('%m/%d/%Y'),
            'end_time_1': self.closed_entry.end_time.strftime('%H:%M:%S'),
        })
        response = self.client.post(self.create_url, overlap_entry, follow=True)
        form = response.context['form']
        self.assertEquals(len(form.errors), 1, form.errors)
        self.assertTrue('__all__' in form.errors, form.errors.keys())

    def testCreateBlockByCurrent(self):
        """
        Test that the entry is blocked by the current entry when appropriate
        """
        overlap_entry = self.default_data
        overlap_entry.update({
            'start_time_0': self.current_entry.start_time.strftime('%m/%d/%Y'),
            'start_time_1': self.current_entry.start_time.strftime('%H:%M:%S'),
            'end_time_0': self.now.strftime('%m/%d/%Y'),
            'end_time_1': self.now.strftime('%H:%M:%S'),
        })
        response = self.client.post(self.create_url, overlap_entry, follow=True)
        form = response.context['form']
        self.assertEquals(len(form.errors), 1, form.errors)
        self.assertTrue('__all__' in form.errors, form.errors.keys())

    def testCreateTooLongEntry(self):
        """
        Test that the entry is blocked if the duration is too long.
        """
        long_entry = self.default_data
        end_time = self.now + relativedelta(hours=13)
        long_entry.update({
            'start_time_0': self.now.strftime('%m/%d/%Y'),
            'start_time_1': self.now.strftime('%H:%M:%S'),
            'end_time_0': end_time.strftime('%m/%d/%Y'),
            'end_time_1': end_time.strftime('%H:%M:%S'),
        })
        response = self.client.post(self.create_url, long_entry, follow=True)
        err_msg = 'Ending time exceeds starting time by 12 hours ' \
            'or more for {0} on {1} at {2} to {3} at {4}.'.format(
                self.project,
                self.now.strftime('%m/%d/%Y'),
                self.now.strftime('%H:%M:%S'),
                end_time.strftime('%m/%d/%Y'),
                end_time.strftime('%H:%M:%S')
            )
        self.assertFormError(response, 'form', None, err_msg)

    def testCreateLongPauseEntry(self):
        """
        Test that the entry is blocked if the duration is too long.
        """
        long_pause = self.default_data
        long_pause['seconds_paused'] = 60 * 60 * 13
        self.client.post(self.create_url, long_pause, follow=True)

    def testProjectList(self):
        """
        Make sure the list of available projects conforms to user associations
        """
        response = self.client.get(reverse('create_entry'))
        self.assertEqual(response.status_code, 200)
        projects = list(response.context['form'].fields['project'].queryset)
        self.assertTrue(self.project in projects)
        self.assertTrue(self.project2 not in projects)
        self.project.status.enable_timetracking = False
        self.project.status.save()
        response = self.client.get(reverse('create_entry'))
        projects = list(response.context['form'].fields['project'].queryset)
        self.assertTrue(self.project not in projects)

    def testBadActivity(self):
        """
        Make sure the user cannot add an entry for an activity that is not in
        the project's activity group
        """
        data = self.default_data
        data.update({'activity': self.sick_activity.id})
        response = self.client.post(self.create_url, data)
        err_msg = 'sick/personal is not allowed for this project. Please '
        err_msg += 'choose among development, and Work'
        self.assertFormError(response, 'form', None, err_msg)

    def add_entry_test_helper(self):
        self.login_user(self.user)

        response = self.client.post(self.create_url, data=self.default_data, follow=True)
        self.assertEqual(response.status_code, 200)

        msg = ('You cannot add/edit entries after a timesheet has been '
               'approved or invoiced. Please correct the start and end times.')
        self.assertEqual([msg], response.context['form'].non_field_errors())

    def test_add_approved_entries(self):
        """
        If your entries have been verified and then approved, you should
        not be able to add entries for that time period
        """
        entry = factories.Entry(**{
            'user': self.user,
            'start_time': self.ten_min_ago,
            'end_time': self.ten_min_ago + relativedelta(minutes=1)
        })
        entry.status = Entry.INVOICED
        entry.save()

        self.add_entry_test_helper()

    def test_add_invoiced_entries(self):
        """
        If your entries have been verified, approved, and invoiced, you
        should not be able to add entries for that time period
        """
        entry = factories.Entry(**{
            'user': self.user,
            'start_time': self.ten_min_ago,
            'end_time': self.ten_min_ago + relativedelta(minutes=1)
        })
        entry.status = Entry.INVOICED
        entry.save()

        self.add_entry_test_helper()

    def edit_entry_helper(self, status='approved'):
        """Helper function for editing approved entries"""
        entry = factories.Entry(**{
            'user': self.user,
            'project': self.project,
            'start_time': self.now - relativedelta(hours=6),
            'end_time': self.now - relativedelta(hours=5),
            'status': status
        })
        url = reverse('edit_entry', args=(entry.pk,))

        data = self.default_data
        data.update({
            'start_time_0': entry.start_time.strftime('%m/%d/%Y'),
            'start_time_1': entry.start_time.strftime('%H:%M:%S'),
            'end_time_0': entry.end_time.strftime('%m/%d/%Y'),
            'end_time_1': entry.end_time.strftime('%H:%M:%S'),
        })

        return url, entry, data

    def test_admin_edit_approved_entry(self):
        """
        An administrator (or anyone with view_payroll_summary perm) should
        be able to edit an entry even if the entries have been approved
        """
        self.client.logout()
        self.login_user(self.superuser)

        url, entry, data = self.edit_entry_helper()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url, data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The entry has been updated successfully.')

        self.assertEqual(self.user, entry.user)

    def test_user_edit_approved_entry(self):
        """A regular user shouldnt be able to edit an approved entry"""
        url, entry, data = self.edit_entry_helper()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 404)

    def test_user_cannot_edit_invoiced_entry(self):
        """User should not be able to edit an invoiced entry"""
        url, entry, data = self.edit_entry_helper(Entry.INVOICED)

        response = self.client.post(url, data=data, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_superuser_can_edit_invoiced_entry(self):
        """Superuser should be able to edit an invoiced entry"""
        self.client.logout()
        self.login_user(self.superuser)

        url, entry, data = self.edit_entry_helper(Entry.INVOICED)

        response = self.client.post(url, data=data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The entry has been updated successfully.')


class StatusTest(ViewTestMixin, TestCase):

    def setUp(self):
        super(StatusTest, self).setUp()

        self.user = factories.User()
        self.user2 = factories.User()
        self.superuser = factories.Superuser()
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename__in=('can_clock_in', 'can_clock_out',
                          'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
        self.user.save()
        self.user2.save()
        self.activity = factories.Activity(code='WRK', name='Work')
        self.devl_activity = factories.Activity(
            code='devl', name='development', billable=True)
        self.sick_activity = factories.Activity(
            code="sick", name="sick/personal", billable=False)
        self.activity_group_all = factories.ActivityGroup(name='All')
        self.activity_group_work = factories.ActivityGroup(name='Client work')

        activities = Activity.objects.all()
        for activity in activities:
            activity.activity_group.add(self.activity_group_all)
            if activity != self.sick_activity:
                activity.activity_group.add(self.activity_group_work)
        self.business = factories.Business()
        status = factories.StatusAttribute(
            label='Current', enable_timetracking=True)
        type_ = factories.TypeAttribute(
            label='Web Sites', enable_timetracking=True)
        self.project = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user, activity_group=self.activity_group_work)
        self.project2 = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user2, activity_group=self.activity_group_all)
        factories.ProjectRelationship(user=self.user, project=self.project)
        self.location = factories.Location()

        self.login_user(self.user)
        self.now = timezone.now()
        self.from_date = utils.get_month_start(self.now)
        self.sheet_url = reverse('view_user_timesheet', args=[self.user.pk])

    def verify_url(self, user=None, from_date=None):
        user = user or self.user
        from_date = from_date or self.from_date
        base_url = reverse('change_user_timesheet', args=(user.pk, 'verify'))
        params = {'from_date': from_date.strftime('%Y-%m-%d')}
        params = urlencode(params)
        return '{0}?{1}'.format(base_url, params)

    def approve_url(self, user=None, from_date=None):
        user = user or self.user
        from_date = from_date or self.from_date
        base_url = reverse('change_user_timesheet', args=(user.pk, 'approve'))
        params = {'from_date': from_date.strftime('%Y-%m-%d')}
        params = urlencode(params)
        return '{0}?{1}'.format(base_url, params)

    def get_reject_url(self, entry_id):
        "Helper for the reject entry view"
        return reverse('reject_entry', args=[entry_id])

    def login_as_admin(self):
        "Helper to login as an admin user"
        self.admin = factories.Superuser()
        self.login_user(self.admin)

    def login_with_permissions(self, *codenames):
        """Helper to login as a user with correct permissions"""
        perms = Permission.objects.filter(codename__in=codenames)
        self.perm_user = factories.User()
        self.perm_user.user_permissions.add(*perms)
        self.perm_user.save()
        self.login_user(self.perm_user)

    def test_verify_link(self):
        factories.Entry(
            user=self.user,
            start_time=self.now - relativedelta(hours=1),
            end_time=self.now
        )

        response = self.client.get(self.sheet_url)
        self.assertTrue(response.status_code, 200)
        self.assertTrue(response.context['show_verify'])
        self.assertFalse(response.context['show_approve'])

    def test_approve_link_no_permission(self):
        """Permission is required to see approve timesheet link."""
        factories.Entry(
            user=self.user,
            start_time=self.now - relativedelta(hours=1),
            end_time=self.now,
            status=Entry.VERIFIED
        )
        response = self.client.get(self.sheet_url)
        self.assertFalse(response.context['show_approve'])

    def test_approve_link(self):
        self.login_with_permissions('view_entry_summary', 'approve_timesheet')
        factories.Entry(
            user=self.user,
            start_time=self.now - relativedelta(hours=1),
            end_time=self.now,
            status=Entry.VERIFIED,
        )
        response = self.client.get(self.sheet_url)
        self.assertEquals(response.status_code, 200)

        self.assertTrue(response.context['show_approve'])
        self.assertFalse(response.context['show_verify'])

    def test_no_hours_verify(self):
        response = self.client.get(self.verify_url(), follow=True)
        self.assertEquals(response.status_code, 200)

        msg = 'You cannot verify/approve a timesheet with no hours'
        messages = response.context['messages']
        self.assertEquals(messages._loaded_messages[0].message, msg)

        response = self.client.post(self.verify_url(), follow=True)
        self.assertEquals(messages._loaded_messages[0].message, msg)

    def test_no_hours_approve(self):
        self.login_with_permissions('approve_timesheet', 'view_entry_summary')
        response = self.client.get(self.approve_url(), follow=True)
        self.assertEquals(response.status_code, 200)

        msg = 'You cannot verify/approve a timesheet with no hours'
        messages = response.context['messages']
        self.assertEquals(messages._loaded_messages[0].message, msg)

        response = self.client.post(self.approve_url(), follow=True)
        self.assertEquals(messages._loaded_messages[0].message, msg)

    def test_verify_other_user(self):
        """A user should not be able to verify another's timesheet"""
        entry = factories.Entry(**{
            'user': self.user2,
            'start_time': self.now - relativedelta(hours=1),
            'end_time': self.now,
        })
        url = self.verify_url(self.user2)
        response = self.client.get(url)

        self.assertEquals(response.status_code, 403)
        self.assertEquals(entry.status, Entry.UNVERIFIED)

        response = self.client.post(url, {'do_action': 'Yes'})
        self.assertEquals(response.status_code, 403)
        self.assertEquals(entry.status, Entry.UNVERIFIED)

    def test_approve_user(self):
        """A regular user should not be able to approve their timesheet"""
        entry = factories.Entry(**{
            'user': self.user,
            'start_time': self.now - relativedelta(hours=1),
            'end_time': self.now
        })

        response = self.client.get(self.approve_url())
        self.assertEquals(response.status_code, 403)

        response = self.client.post(self.approve_url(), {'do_action': 'Yes'})
        self.assertEquals(response.status_code, 403)
        self.assertNotEquals(entry.status, Entry.APPROVED)
        self.assertContains(
            response,
            'Forbidden: You cannot approve this timesheet',
            status_code=403
        )

    def test_approve_other_user(self):
        """A regular user should not be able to approve another's timesheet"""
        entry = factories.Entry(**{
            'user': self.user2,
            'start_time': self.now - relativedelta(hours=1),
            'end_time': self.now
        })

        response = self.client.get(self.approve_url())
        self.assertEquals(response.status_code, 403)

        response = self.client.post(self.approve_url(), {'do_action': 'Yes'})
        self.assertEquals(response.status_code, 403)
        self.assertNotEquals(entry.status, Entry.APPROVED)
        self.assertContains(
            response,
            'Forbidden: You cannot approve this timesheet',
            status_code=403
        )

    def test_verify_active_entry(self):
        """
        A user shouldnt be able to verify a timesheet if it contains
        an active entry and should be redirect back to the ledger
        """
        self.login_as_admin()

        entry1 = factories.Entry(**{
            'user': self.user,
            'start_time': self.now - relativedelta(hours=5),
            'end_time': self.now - relativedelta(hours=4),
            'status': Entry.UNVERIFIED
        })
        entry2 = factories.Entry(**{
            'user': self.user,
            'start_time': self.now - relativedelta(hours=1),
            'status': Entry.UNVERIFIED
        })

        response = self.client.get(self.verify_url(), follow=True)
        self.assertEquals(response.status_code, 200)

        messages = response.context['messages']
        msg = 'You cannot verify/approve this timesheet while the user {0} ' \
            'has an active entry. Please have them close any active ' \
            'entries.'.format(self.user.get_name_or_username())

        self.assertEquals(messages._loaded_messages[0].message, msg)
        self.assertEquals(entry1.status, Entry.UNVERIFIED)
        self.assertEquals(entry2.status, Entry.UNVERIFIED)

        response = self.client.post(self.verify_url(), follow=True)
        self.assertEquals(response.status_code, 200)
        messages = response.context['messages']

        self.assertEquals(messages._loaded_messages[0].message, msg)
        self.assertEquals(entry1.status, Entry.UNVERIFIED)
        self.assertEquals(entry2.status, Entry.UNVERIFIED)

    def testVerifyButton(self):
        response = self.client.get(self.sheet_url)
        self.assertNotContains(response, self.verify_url())
        entry = factories.Entry(**{
            'user': self.user,
            'start_time': timezone.now() - relativedelta(hours=1),
            'end_time':  timezone.now(),
        })
        response = self.client.get(self.sheet_url)
        self.assertTrue(response.context['show_verify'])
        entry.status = Entry.VERIFIED
        entry.save()
        response = self.client.get(self.sheet_url)
        self.assertFalse(response.context['show_verify'])

    def testApproveButton(self):
        self.login_as_admin()
        response = self.client.get(self.sheet_url)
        self.assertFalse(response.context['show_approve'])
        entry = factories.Entry(**{
            'user': self.user,
            'start_time': timezone.now() - relativedelta(hours=1),
            'end_time':  timezone.now(),
        })
        response = self.client.get(self.sheet_url)
        self.assertFalse(response.context['show_approve'])
        entry.status = Entry.VERIFIED
        entry.save()
        response = self.client.get(self.sheet_url)
        self.assertTrue(response.context['show_approve'])
        entry.status = Entry.APPROVED
        entry.save()
        response = self.client.get(self.sheet_url)
        self.assertFalse(response.context['show_approve'])

    def testVerifyPage(self):
        factories.Entry(
            user=self.user,
            start_time=timezone.now() - relativedelta(hours=1),
            end_time=timezone.now(),
        )
        self.client.get(self.verify_url())
        entries = self.user.timepiece_entries.all()
        self.assertEquals(entries[0].status, Entry.UNVERIFIED)
        self.client.post(self.verify_url(), {'do_action': 'Yes'})
        self.assertEquals(entries[0].status, Entry.VERIFIED)

    def testApprovePage(self):
        self.login_with_permissions('approve_timesheet', 'view_entry_summary')
        entry = factories.Entry(
            user=self.user,
            start_time=timezone.now() - relativedelta(hours=1),
            end_time=timezone.now(),
        )

        self.assertEquals(entry.status, Entry.UNVERIFIED)
        entry.status = Entry.VERIFIED
        entry.save()

        self.client.get(self.approve_url(),)
        self.assertEquals(entry.status, Entry.VERIFIED)

        self.client.post(self.approve_url(), {'do_action': 'Yes'})
        entry = Entry.objects.get(pk=entry.pk)
        self.assertEquals(entry.status, Entry.APPROVED)

    def test_reject_user(self):
        """A regular user should not be able to reject an entry"""
        self.login_user(self.user)

        now = timezone.now()
        entry = factories.Entry(**{
            'user': self.user,
            'start_time': now - relativedelta(hours=1),
            'end_time': now,
            'status': Entry.VERIFIED
        })
        url = self.get_reject_url(entry.pk)

        self.client.post(url, {'Yes': 'yes'})
        self.assertEquals(entry.status, Entry.VERIFIED)

    def test_reject_other_user(self):
        """
        A regular user should not be able to reject
        another users entry
        """
        self.login_user(self.user2)

        now = timezone.now()
        entry = factories.Entry(**{
            'user': self.user,
            'start_time': now - relativedelta(hours=1),
            'end_time': now,
            'status': Entry.VERIFIED
        })
        url = self.get_reject_url(entry.pk)

        self.client.post(url, {'Yes': 'yes'})
        self.assertEquals(entry.status, Entry.VERIFIED)

    def testRejectPage(self):
        self.login_as_admin()
        entry = factories.Entry(**{
            'user': self.user,
            'start_time': timezone.now() - relativedelta(hours=1),
            'end_time':  timezone.now(),
        })
        reject_url = self.get_reject_url(entry.id)

        def check_entry_against_code(status, status_code):
            entry.status = status
            entry.save()
            response = self.client.get(reject_url)
            self.assertEqual(response.status_code, status_code)

        check_entry_against_code(Entry.UNVERIFIED, 302)
        check_entry_against_code(Entry.INVOICED, 302)
        check_entry_against_code(Entry.APPROVED, 200)
        check_entry_against_code(Entry.VERIFIED, 200)
        response = self.client.post(reject_url, {'Yes': 'yes'})
        self.assertTrue(response.status_code, 302)
        entry = Entry.objects.get(user=self.user)
        self.assertEqual(entry.status, Entry.UNVERIFIED)

    def testNotAllowedToRejectTimesheet(self):
        entry = factories.Entry(**{
            'user': self.user,
            'start_time': timezone.now() - relativedelta(hours=1),
            'end_time':  timezone.now(),
        })
        reject_url = self.get_reject_url(entry.id)
        response = self.client.get(reject_url)
        self.assertTrue(response.status_code, 403)

    def testNotAllowedToApproveTimesheet(self):
        response = self.client.get(self.approve_url(),)
        self.assertTrue(response.status_code, 403)

    def testNotAllowedToVerifyTimesheet(self):
        self.login_user(self.user2)
        response = self.client.get(self.verify_url(),)
        self.assertTrue(response.status_code, 403)


class TestTotals(ViewTestMixin, LogTimeMixin, TestCase):

    def setUp(self):
        super(TestTotals, self).setUp()

        self.user = factories.User()
        self.user2 = factories.User()
        self.superuser = factories.Superuser()
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename__in=('can_clock_in', 'can_clock_out',
                          'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
        self.user.save()
        self.user2.save()
        self.activity = factories.Activity(code='WRK', name='Work')
        self.devl_activity = factories.Activity(
            code='devl', name='development', billable=True)
        self.sick_activity = factories.Activity(
            code="sick", name="sick/personal", billable=False)
        self.activity_group_all = factories.ActivityGroup(name='All')
        self.activity_group_work = factories.ActivityGroup(name='Client work')

        activities = Activity.objects.all()
        for activity in activities:
            activity.activity_group.add(self.activity_group_all)
            if activity != self.sick_activity:
                activity.activity_group.add(self.activity_group_work)
        self.business = factories.Business()
        status = factories.StatusAttribute(
            label='Current', enable_timetracking=True)
        type_ = factories.TypeAttribute(
            label='Web Sites', enable_timetracking=True)
        self.project = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user, activity_group=self.activity_group_work)
        self.project2 = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user2, activity_group=self.activity_group_all)
        factories.ProjectRelationship(user=self.user, project=self.project)
        self.location = factories.Location()

        self.p1 = factories.BillableProject(name='1')
        self.p2 = factories.NonbillableProject(name='2')
        self.p4 = factories.BillableProject(name='4')
        # For use with daily totals (Same project, non-billable activity)
        self.p3 = factories.NonbillableProject(name='1')

    def testGroupedTotals(self):
        self.login_user(self.user)
        days = [
            utils.add_timezone(datetime.datetime(2010, 12, 20)),
            utils.add_timezone(datetime.datetime(2010, 12, 27)),
            utils.add_timezone(datetime.datetime(2010, 12, 28)),
            utils.add_timezone(datetime.datetime(2011, 1, 3)),
            utils.add_timezone(datetime.datetime(2011, 1, 4)),
            utils.add_timezone(datetime.datetime(2011, 1, 10)),
            utils.add_timezone(datetime.datetime(2011, 1, 16)),
            utils.add_timezone(datetime.datetime(2011, 1, 17)),
            utils.add_timezone(datetime.datetime(2011, 1, 18)),
            utils.add_timezone(datetime.datetime(2011, 2, 2))
        ]
        # Each week has two days of entries, except 12-20, and 2-2 but these
        # are excluded in the timespan queryset
        for day in days:
            self.log_time(project=self.p1, start=day, delta=(1, 0))
            self.log_time(project=self.p4, start=day, delta=(1, 0))
            if random.choice([True, False]):
                self.log_time(project=self.p2, start=day, delta=(1, 0))
            else:
                self.log_time(project=self.p3, start=day, delta=(1, 0))
        date = utils.add_timezone(datetime.datetime(2011, 1, 19))
        from_date = utils.get_month_start(date)
        to_date = from_date + relativedelta(months=1)
        first_week = utils.get_week_start(from_date)
        entries = Entry.objects.timespan(first_week, to_date=to_date)
        totals = grouped_totals(entries)
        for week, week_totals, days in totals:
            # Jan. 3rd is a monday. Each week should be on a monday
            if week.month == 1:
                self.assertEqual(week.day % 7, 3)
            self.assertEqual(week_totals['billable'], 4)
            self.assertEqual(week_totals['non_billable'], 2)
            self.assertEqual(week_totals['total'], 6)
            for day, projects in days:
                for project, totals in projects[1].items():
                    self.assertEqual(projects[0]['billable'], 2)
                    self.assertEqual(projects[0]['non_billable'], 1)
                    self.assertEqual(projects[0]['total'], 3)
                    if project == self.p1:
                        self.assertEqual(totals['billable'], 1)
                        self.assertEqual(totals['total'], 1)
                    if project == self.p2:
                        self.assertEqual(totals['non_billable'], 1)
                        self.assertEqual(totals['total'], 1)
                    if project == self.p3:
                        self.assertEqual(totals['billable'], 1)
                        self.assertEqual(totals['non_billable'], 1)
                        self.assertEqual(totals['total'], 2)
                    if project == self.p4:
                        self.assertEqual(totals['billable'], 1)
                        self.assertEqual(totals['total'], 1)


class HourlySummaryTest(ViewTestMixin, TestCase):

    def setUp(self):
        super(HourlySummaryTest, self).setUp()

        self.user = factories.User()
        self.user2 = factories.User()
        self.superuser = factories.Superuser()
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename__in=('can_clock_in', 'can_clock_out',
                          'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
        self.user.save()
        self.user2.save()
        self.activity = factories.Activity(code='WRK', name='Work')
        self.devl_activity = factories.Activity(
            code='devl', name='development', billable=True)
        self.sick_activity = factories.Activity(
            code="sick", name="sick/personal", billable=False)
        self.activity_group_all = factories.ActivityGroup(name='All')
        self.activity_group_work = factories.ActivityGroup(name='Client work')

        activities = Activity.objects.all()
        for activity in activities:
            activity.activity_group.add(self.activity_group_all)
            if activity != self.sick_activity:
                activity.activity_group.add(self.activity_group_work)
        self.business = factories.Business()
        status = factories.StatusAttribute(
            label='Current', enable_timetracking=True)
        type_ = factories.TypeAttribute(
            label='Web Sites', enable_timetracking=True)
        self.project = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user, activity_group=self.activity_group_work)
        self.project2 = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user2, activity_group=self.activity_group_all)
        factories.ProjectRelationship(user=self.user, project=self.project)
        self.location = factories.Location()

        self.now = timezone.now()
        self.month = self.now.replace(day=1)
        self.url = reverse('view_user_timesheet', args=(self.user.pk,))
        self.login_user(self.user)

    def create_month_entries(self):
        """Create four entries, one for each week of the month"""
        factories.Entry(
            user=self.user,
            start_time=self.month,
            end_time=self.month + relativedelta(hours=1)
        )
        factories.Entry(
            user=self.user,
            start_time=self.month + relativedelta(weeks=1),
            end_time=self.month + relativedelta(weeks=1, hours=1)
        )
        factories.Entry(
            user=self.user,
            start_time=self.month + relativedelta(weeks=2),
            end_time=self.month + relativedelta(weeks=2, hours=1)
        )
        factories.Entry(
            user=self.user,
            start_time=self.month + relativedelta(weeks=3),
            end_time=self.month + relativedelta(weeks=3, hours=1)
        )

    def test_start_of_week(self):
        """Test that the entries start being labeled on the first week, ISO"""
        self.create_month_entries()

        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)

        start_date = utils.get_week_start(self.month)
        # Week of {{ week|date:'M j, Y'}}
        msg = 'Week of {0}'.format(start_date.strftime('%b %d, %Y')).replace(" 0", " ")
        self.assertContains(response, msg)

    def test_contains_only_current_entries(self):
        """
        Only entries from the current month should be displayed
        using default data from create_month_entries()
        """
        self.create_month_entries()
        old_entry = factories.Entry(**{
            'user': self.user,
            'start_time': self.month - relativedelta(days=1, hours=1),
            'end_time': self.month - relativedelta(days=1)
        })

        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)
        self.assertFalse(old_entry in response.context['entries'])

    def test_single_entry_in_week(self):
        """
        When there is a single entry at the end of an ISO week,
        the view should show the entries from that entire week
        even though they belong in the previous month.

        This occurs in April 2012, so we are using that month
        as the basis for out test case
        """
        april = utils.add_timezone(
            datetime.datetime(month=4, day=1, year=2012)
        )
        march = utils.add_timezone(
            datetime.datetime(month=3, day=26, year=2012)
        )
        factories.Entry(**{
            'user': self.user,
            'start_time': april,
            'end_time': april + relativedelta(hours=1)
        })
        factories.Entry(**{
            'user': self.user,
            'start_time': april + relativedelta(weeks=1),
            'end_time': april + relativedelta(weeks=1, hours=1)
        })
        factories.Entry(**{
            'user': self.user,
            'start_time': march,
            'end_time': march + relativedelta(hours=1)
        })

        response = self.client.get(self.url + '?{0}'.format(
            urlencode({'year': 2012, 'month': 4})
        ))
        self.assertEquals(response.status_code, 200)
        # entries context object is a ValuesQuerySet
        extra_values = ('start_time', 'end_time', 'comments', 'seconds_paused',
                        'id', 'location__name', 'project__name',
                        'activity__name', 'status')
        entries = Entry.objects.timespan(april, span='month').date_trunc('month', extra_values)
        self.assertEquals(list(entries), list(response.context['entries']))


class MonthlyRejectTestCase(ViewTestMixin, TestCase):

    def setUp(self):
        super(MonthlyRejectTestCase, self).setUp()

        self.user = factories.User()
        self.user2 = factories.User()
        self.superuser = factories.Superuser()
        permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename__in=('can_clock_in', 'can_clock_out',
                          'can_pause', 'change_entry')
        )
        self.user.user_permissions = permissions
        self.user2.user_permissions = permissions
        self.user.save()
        self.user2.save()
        self.activity = factories.Activity(code='WRK', name='Work')
        self.devl_activity = factories.Activity(
            code='devl', name='development', billable=True)
        self.sick_activity = factories.Activity(
            code="sick", name="sick/personal", billable=False)
        self.activity_group_all = factories.ActivityGroup(name='All')
        self.activity_group_work = factories.ActivityGroup(name='Client work')

        activities = Activity.objects.all()
        for activity in activities:
            activity.activity_group.add(self.activity_group_all)
            if activity != self.sick_activity:
                activity.activity_group.add(self.activity_group_work)
        self.business = factories.Business()
        status = factories.StatusAttribute(
            label='Current', enable_timetracking=True)
        type_ = factories.TypeAttribute(
            label='Web Sites', enable_timetracking=True)
        self.project = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user, activity_group=self.activity_group_work)
        self.project2 = factories.Project(
            type=type_, status=status, business=self.business,
            point_person=self.user2, activity_group=self.activity_group_all)
        factories.ProjectRelationship(user=self.user, project=self.project)
        self.location = factories.Location()

        self.now = timezone.now()
        self.data = {
            'month': self.now.month,
            'year': self.now.year,
            'yes': 'Yes'
        }
        self.url = reverse('reject_user_timesheet', args=(self.user.pk,))

    def create_entries(self, date, status):
        """Create entries using a date and with a given status"""
        factories.Entry(**{
            'user': self.user,
            'start_time': date,
            'end_time': date + relativedelta(hours=1),
            'status': status
        })
        factories.Entry(**{
            'user': self.user,
            'start_time': date + relativedelta(hours=2),
            'end_time': date + relativedelta(hours=3),
            'status': status
        })

    def test_page_permissions(self):
        """
        An admin should have the permission to reject a users entries
        and unverify them
        """
        self.login_user(self.superuser)
        self.create_entries(self.now, Entry.VERIFIED)

        response = self.client.get(self.url, data=self.data)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(self.url, data=self.data)

        entries = Entry.no_join.filter(status=Entry.VERIFIED)
        self.assertEquals(entries.count(), 0)

    def test_page_no_permissions(self):
        """
        A regular user should not have the permissions to
        get or post to the page
        """
        self.login_user(self.user)
        self.create_entries(timezone.now(), Entry.VERIFIED)

        response = self.client.get(self.url, data=self.data)
        self.assertEqual(response.status_code, 302)

        response = self.client.post(self.url, data=self.data)

        entries = Entry.no_join.filter(status=Entry.VERIFIED)
        self.assertEquals(entries.count(), 2)

    def test_reject_entries_no_date(self):
        """
        If you are missing the month/year used to filter the entries
        then the reject page should not show
        """
        self.login_user(self.superuser)
        self.create_entries(timezone.now(), Entry.VERIFIED)

        data = {
            'month': self.now.month
        }
        response = self.client.get(self.url, data=data)
        self.assertEqual(response.status_code, 302)

        data = {
            'year': self.now.year
        }
        response = self.client.get(self.url, data=data)
        self.assertEqual(response.status_code, 302)

    def test_reject_entries_no_confirm(self):
        """
        If a post request contains the month/year but is missing the key
        'yes', then the entries are not rejected
        """
        self.login_user(self.superuser)
        self.create_entries(timezone.now(), Entry.VERIFIED)

        data = self.data
        data.pop('yes')

        self.client.post(self.url, data=data)

        entries = Entry.no_join.filter(status=Entry.VERIFIED)
        self.assertEquals(entries.count(), 2)

    def test_reject_approved_invoiced_entries(self):
        """Entries that are approved invoiced should not be rejected"""
        self.login_user(self.superuser)
        self.create_entries(timezone.now(), Entry.APPROVED)
        self.create_entries(timezone.now(), Entry.INVOICED)

        self.client.post(self.url, data=self.data)

        entries = Entry.no_join.filter(status=Entry.UNVERIFIED)
        self.assertEquals(entries.count(), 0)
