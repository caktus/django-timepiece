import time
import datetime
import random
import itertools
import urllib
from decimal import Decimal

from django.core.urlresolvers import reverse

from django.contrib.auth.models import User, Permission
from django.core.exceptions import ValidationError
from django.forms import model_to_dict

from timepiece.tests.base import TimepieceDataTestCase

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms
from timepiece import utils

from dateutil.relativedelta import relativedelta


class EditableTest(TimepieceDataTestCase):
    def setUp(self):
        super(EditableTest, self).setUp()
        self.day_period = timepiece.RepeatPeriod.objects.create(
            count=2,
            interval='day',
            active=True,
        )
        self.timesheet = timepiece.PersonRepeatPeriod.objects.create(
            user=self.user,
            repeat_period=self.day_period
        )
        self.billing_window = timepiece.BillingWindow.objects.create(
            period=self.day_period,
            date=datetime.datetime.now() - datetime.timedelta(days=8),
            end_date=datetime.datetime.now() - datetime.timedelta(days=8) \
            + self.day_period.delta(),
        )
        self.entry = self.create_entry({
            'user': self.user,
            'project': self.project,
            'start_time': datetime.datetime.now() - datetime.timedelta(days=6),
            'end_time':  datetime.datetime.now() - datetime.timedelta(days=6),
            'seconds_paused': 0,
            'status': 'verified',
        })
        self.entry2 = self.create_entry({
            'user': self.user,
            'project': self.project,
            'start_time': datetime.datetime.now() - datetime.timedelta(days=2),
            'end_time':  datetime.datetime.now() - datetime.timedelta(days=2),
            'seconds_paused': 0,
            'status': 'unverified',
        })
        timepiece.RepeatPeriod.objects.update_billing_windows()

    def testUnEditable(self):
        self.assertFalse(self.entry.is_editable)

    def testEditable(self):
        self.assertTrue(self.entry2.is_editable)


class MyLedgerTest(TimepieceDataTestCase):
    def setUp(self):
        super(MyLedgerTest, self).setUp()
        self.month_period = timepiece.RepeatPeriod.objects.create(
            count=1,
            interval='month',
            active=True,
        )
        self.timesheet = timepiece.PersonRepeatPeriod.objects.create(
            user=self.user,
            repeat_period=self.month_period
        )
        self.billing_window = timepiece.BillingWindow.objects.create(
            period=self.month_period,
            date=datetime.datetime.now(),
            end_date=datetime.datetime.now() + self.month_period.delta()
        )
        self.url = reverse('view_person_time_sheet', kwargs={
            'person_id': self.user.pk,
            'period_id': self.timesheet.repeat_period.pk,
        })

    def testEmptyTimeSheet(self):
        self.client.login(username='user', password='abc')
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)

    def testEmptyHourlySummary(self):
        self.client.login(username='user', password='abc')
        response = self.client.get(reverse('view_person_time_sheet', kwargs={
            'person_id': self.user.pk,
            'period_id': self.timesheet.repeat_period.pk,
            'hourly': 'hourly',
        }))
        self.assertEquals(response.status_code, 200)

    def testNotMyLedger(self):
        self.client.login(username='user2', password='abc')
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 403)

    def testNoLedger(self):
        self.client.login(username='user2', password='abc')
        self.url = reverse('timepiece-entries')
        try:
            response = self.client.get(self.url)
        except Exception, e:
            self.fail(e)


class ClockInTest(TimepieceDataTestCase):
    def setUp(self):
        super(ClockInTest, self).setUp()
        self.url = reverse('timepiece-clock-in')
        self.now = datetime.datetime.now()
        self.ten_min_ago = self.now - datetime.timedelta(minutes=10)
        self.clock_in_form = {
            'project': self.project.pk,
            'location': self.location.pk,
            'activity': self.devl_activity.pk,
            'start_time_0': self.ten_min_ago.strftime('%m/%d/%Y'),
            'start_time_1': self.ten_min_ago.strftime('%H:%M:%S'),
        }

    def testClockIn(self):
        """
        Test the simplest clock in scenario
        """
        self.client.login(username='user', password='abc')
        data = self.clock_in_form
        response = self.client.post(self.url, data, follow=True)
        # Clock in form submission leads to the dashboard page
        # with one active entry
        self.assertRedirects(response, reverse('timepiece-entries'),
                             status_code=302, target_status_code=200)
        self.assertContains(response, 'You have clocked into', count=1)
        self.assertEquals(len(response.context['my_active_entries']), 1)

    def testClockInAutoOut(self):
        """
        Clocking in during an active entry automatically clocks out the current
        entry one second before the new entry.
        """
        self.client.login(username='user', password='abc')
        entry1 = self.create_entry({
            'start_time': self.ten_min_ago,
        })
        data = self.clock_in_form
        data.update({
            'start_time_0': self.now.strftime('%m/%d/%Y'),
            'start_time_1': self.now.strftime('%H:%M:%S'),
        })
        response = self.client.post(self.url, data)
        entries = timepiece.Entry.objects.all()
        #These clock in times do not overlap
        for entry in entries:
            if entry.is_overlapping():
                self.fail('Overlapping Times')
        #There is one closed entry and open current entry
        closed_entry = entries.get(end_time__isnull=False)
        current_entry = entries.get(end_time__isnull=True)
        #The current start time is one second after the closed entry's end time
        self.assertEqual(closed_entry.end_time + datetime.timedelta(seconds=1),
                         current_entry.start_time)

    def testClockInPause(self):
        """
        Test that the user can clock in while the current entry is paused.
        The current entry will be clocked out.
        """
        self.client.login(username='user', password='abc')
        entry1 = self.create_entry({
            'start_time': self.ten_min_ago,
        })
        e_id = timepiece.Entry.objects.get(pk=entry1.id)
        e_id.pause()
        data = self.clock_in_form
        data.update({
            'start_time_0': self.now.strftime('%m/%d/%Y'),
            'start_time_1': self.now.strftime('%H:%M:%S'),
        })
        response = self.client.post(self.url, data, follow=True)
        #obtain entry1 now that it is closed. The hours should be recorded
        e_id = timepiece.Entry.objects.get(pk=entry1.id)
        self.assertTrue(e_id.is_closed)
        self.assertTrue(e_id.hours)

    def testClockInBlock(self):
        """
        The user cannot clock in to a time that is already logged
        """
        self.client.login(username='user', password='abc')
        entry1_data = {
            'project': self.project,
            'activity': self.devl_activity,
            'start_time': self.ten_min_ago,
            'end_time': self.now,
        }
        entry1 = self.create_entry(entry1_data)
        entry1_data.update({
            'st_str': self.ten_min_ago.strftime('%H:%M:%S'),
            'end_str': self.now.strftime('%H:%M:%S'),
        })
        blocked_start_time = entry1.start_time + datetime.timedelta(minutes=5)
        data = self.clock_in_form
        data.update({
            'start_time_0': blocked_start_time.strftime('%m/%d/%Y'),
            'start_time_1': blocked_start_time.strftime('%H:%M:%S'),
        })
        #This clock in attempt should be blocked by entry1
        response = self.client.post(self.url, data)
        self.assertFormError(response, 'form', None, \
            'Start time overlaps with: ' + \
            '%(project)s - %(activity)s - from %(st_str)s to %(end_str)s' % \
            entry1_data)

    def testClockInSameTime(self):
        """
        Test that the user cannot clock in with the same start time as the
        active entry
        """
        self.client.login(username='user', password='abc')
        entry1_data = {
            'start_time': self.now,
            'project': self.project,
            'activity': self.devl_activity,
        }
        entry1 = self.create_entry(entry1_data)
        entry1_data.update({
            'st_str': self.now.strftime('%H:%M:%S')
        })
        data = self.clock_in_form
        data.update({
            'start_time_0': entry1.start_time.strftime('%m/%d/%Y'),
            'start_time_1': entry1.start_time.strftime('%H:%M:%S'),
        })
        #This clock in attempt should be blocked by entry1 (same start time)
        response = self.client.post(self.url, data)
        self.assertFormError(response, 'form', None, \
            'Please enter a valid start time')
        self.assertFormError(response, 'form', 'start_time', \
            'The start time is on or before the current entry: ' + \
            '%(project)s - %(activity)s starting at %(st_str)s' % entry1_data)

    def testClockInBeforeCurrent(self):
        """
        Test that the user cannot clock in with a start time before the active
        entry
        """
        self.client.login(username='user', password='abc')
        entry1_data = {
            'project': self.project,
            'activity': self.devl_activity,
            'start_time': self.ten_min_ago,
        }
        entry1 = self.create_entry(entry1_data)
        entry1_data.update({
            'st_str': self.ten_min_ago.strftime('%H:%M:%S')
        })
        before_entry1 = entry1.start_time - datetime.timedelta(minutes=5)
        data = self.clock_in_form
        data.update({
            'start_time_0': before_entry1.strftime('%m/%d/%Y'),
            'start_time_1': before_entry1.strftime('%H:%M:%S'),
        })
        #This clock in attempt should be blocked by entry1
        #(It is before the start time of the current entry)
        response = self.client.post(self.url, data)
        self.assertFormError(response, 'form', None, \
            'Please enter a valid start time')
        self.assertFormError(response, 'form', 'start_time', \
            'The start time is on or before the current entry: ' + \
            '%(project)s - %(activity)s starting at %(st_str)s' % entry1_data)

    def testProjectListFiltered(self):
        self.client.login(username='user', password='abc')
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)
        projects = list(response.context['form'].fields['project'].queryset)
        self.assertTrue(self.project in projects)
        self.assertFalse(self.project2 in projects)

    def testClockInLogin(self):
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 302)
        self.client.login(username='user', password='abc')
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)

    def testClockInUnauthorizedProject(self):
        self.client.login(username='user', password='abc')
        data = self.clock_in_form
        data.update({'project': self.project2.id})
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        err_msg = 'Select a valid choice. That choice is not one of the ' + \
                  'available choices.'
        self.assertFormError(response, 'form', 'project', err_msg)

    def testClockInBadActivity(self):
        self.client.login(username='user', password='abc')
        data = self.clock_in_form
        data.update({
            'project': self.project.id,
            'activity': self.sick_activity.id,
        })
        response = self.client.post(self.url, data)        
        err_msg = 'sick/personal is not allowed for this project. Please '
        err_msg += 'choose among development, and Work'
        self.assertFormError(response, 'form', None, err_msg)


class AutoActivityTest(TimepieceDataTestCase):
    """Test the initial value chosen for activity on clock in form"""
    def setUp(self):
        super(AutoActivityTest, self).setUp()

    def get_activity(self, project=None):
        if not project:
            project = self.project
        initial = {'project': project.id}
        form = timepiece_forms.ClockInForm(user=self.user, initial=initial)
        return form.initial['activity']

    def testNewWorker(self):
        """The worker has 0 entries on this project. Activity should = None"""
        self.client.login(username='user', password='abc')
        self.assertEqual(self.get_activity(), None)

    def testLastWorkedOneEntry(self):
        """The worker has one previous entry on the project"""
        self.client.login(username='user', password='abc')
        self.log_time(project=self.project, activity=self.devl_activity)
        self.assertEqual(self.get_activity(), self.devl_activity.id)

    def testLastWorkedSeveralEntries(self):
        """The worker has several entries on a project. Use the most recent"""
        self.client.login(username='user', password='abc')
        for day in xrange(0, 10):
            this_day = datetime.datetime(2011, 1, 1)
            this_day += datetime.timedelta(days=day)
            activity = self.activity if day == 9 else self.devl_activity
            self.log_time(start=this_day, project=self.project,
                          activity=activity)
        self.assertEqual(self.get_activity(), self.activity.id)

    def testLastWorkedSeveralProjects(self):
        """
        Obtain activities contingent on the project when worker is on several
        """
        self.client.login(username='user', password='abc')
        project1 = self.project
        project2 = self.project2
        for day in xrange(0, 10):
            this_day = datetime.datetime(2011, 1, 1)
            this_day += datetime.timedelta(days=day)
            #Cycle through projects and activities
            project = project1 if day % 2 == 0 else project2
            activity = self.devl_activity if day % 3 == 0 else self.activity
            self.log_time(start=this_day, project=project, activity=activity)
        self.assertEqual(self.get_activity(project1), self.activity.id)
        self.assertEqual(self.get_activity(project2), self.devl_activity.id)


class ClockOutTest(TimepieceDataTestCase):
    def setUp(self):
        super(ClockOutTest, self).setUp()
        self.client.login(username='user', password='abc')
        #create an open entry via clock in, so clock out tests don't have to
        self.default_end_time = datetime.datetime.now()
        back = datetime.datetime.now() - datetime.timedelta(hours=5)
        entry = self.create_entry({
            'user': self.user,
            'start_time': back,
            'project': self.project,
            'activity': self.devl_activity,
        })
        clock_in_data = {
            'project': self.project.id,
            'location': self.location.pk,
            'activity': self.devl_activity.pk,
            'start_time_0': back.strftime('%m/%d/%Y'),
            'start_time_1': back.strftime('%H:%M:%S'),
        }
        clock_in_url = reverse('timepiece-clock-in')
        response = self.client.post(clock_in_url, clock_in_data, follow=True)
        entry.save()
        #establish entry and url for all tests
        self.entry = timepiece.Entry.objects.get(pk=entry.pk)
        self.url = reverse('timepiece-clock-out', args=[entry.pk])

    def testBasicClockOut(self):
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
        closed_entry = timepiece.Entry.objects.get(pk=self.entry.pk)
        self.assertTrue(closed_entry.is_closed)

    def testClockOutWithSecondsPaused(self):
        """
        Test that clocking out of an unpaused entry with previous pause time
        calculates the correct amount of unpaused time.
        """
        entry_with_pause = self.entry
        #paused for a total of 1 hour
        entry_with_pause.seconds_paused = 3600
        entry_with_pause.save()
        data = {
            'start_time_0': entry_with_pause.start_time.strftime('%m/%d/%Y'),
            'start_time_1': entry_with_pause.start_time.strftime('%H:%M:%S'),
            'end_time_0': self.default_end_time.strftime('%m/%d/%Y'),
            'end_time_1': self.default_end_time.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        response = self.client.post(
            reverse('timepiece-clock-out', args=[entry_with_pause.pk]), data)
        entry_with_pause = timepiece.Entry.objects.get(pk=entry_with_pause.pk)
        self.assertAlmostEqual(entry_with_pause.hours, 4)

    def testClockOutWhilePaused(self):
        """
        Test that clocking out of a paused entry calculates the correct time
        """
        paused_entry = self.entry
        paused_entry.pause_time = self.entry.start_time \
            + datetime.timedelta(hours=1)
        paused_entry.save()
        data = {
            'start_time_0': paused_entry.start_time.strftime('%m/%d/%Y'),
            'start_time_1': paused_entry.start_time.strftime('%H:%M:%S'),
            'end_time_0': self.default_end_time.strftime('%m/%d/%Y'),
            'end_time_1': self.default_end_time.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        response = self.client.post(
            reverse('timepiece-clock-out', args=[paused_entry.pk]), data)
        paused_entry = timepiece.Entry.objects.get(pk=paused_entry.pk)
        self.assertAlmostEqual(paused_entry.hours, 1)

    def testClockOutReverse(self):
        """
        Test that the user can't clock out at a time prior to the starting time
        """
        backward_entry = self.entry
        backward_entry.save()
        #reverse the times
        data = {
            'start_time_0': self.default_end_time.strftime('%m/%d/%Y'),
            'start_time_1': self.default_end_time.strftime('%H:%M:%S'),
            'end_time_0': self.entry.start_time.strftime('%m/%d/%Y'),
            'end_time_1': self.entry.start_time.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        response = self.client.post(
            reverse('timepiece-clock-out', args=[backward_entry.pk]), data)
        self.assertFormError(response, 'form', None,
            'Ending time must exceed the starting time')

    def testClockOutOverlap(self):
        """
        Test that the user cannot clock out if the times overlap with an
        existing entry
        """
        #Create a closed and valid entry
        now = datetime.datetime.now() - datetime.timedelta(hours=5)
        entry1_data = ({
            'user': self.user,
            'project': self.project,
            'activity': self.devl_activity,
            'start_time': now,
            'end_time': self.default_end_time
        })
        entry1 = self.create_entry(entry1_data)
        entry1_data.update({
            'st_str': entry1.start_time.strftime('%H:%M:%S'),
            'end_str': entry1.end_time.strftime('%H:%M:%S'),
        })
        #Create a form with times that overlap with entry1
        bad_start = entry1.start_time - datetime.timedelta(hours=1)
        bad_end = entry1.end_time + datetime.timedelta(hours=1)
        bad_entry = self.create_entry({
            'user': self.user,
            'start_time': bad_start,
        })
        data = {
            'start_time_0': bad_start.strftime('%m/%d/%Y'),
            'start_time_1': bad_start.strftime('%H:%M:%S'),
            'end_time_0': bad_end.strftime('%m/%d/%Y'),
            'end_time_1': bad_end.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        #With entry1 on either side, a post with the bad_entry data should fail
        response = self.client.post(
            reverse('timepiece-clock-out', args=[bad_entry.pk]), data)
        self.assertFormError(response, 'form', None,
            'Start time overlaps with: ' + \
            '%(project)s - %(activity)s - from %(st_str)s to %(end_str)s' %
            entry1_data)


class CheckOverlap(TimepieceDataTestCase):
    """
    With entry overlaps, entry.check_overlap method should return True
    With valid entries, check_overlap should return False
    """
    def setUp(self):
        super(CheckOverlap, self).setUp()
        self.client.login(username='user', password='abc')
        self.now = datetime.datetime.now()
        #define start and end times to create valid entries
        self.start = self.now - datetime.timedelta(days=0, hours=8)
        self.end = self.now - datetime.timedelta(days=0)
        #Create a valid entry for the tests to overlap with
        self.log_time(start=self.start, end=self.end)
        #define bad start times relative to the valid one (just in/outside)
        self.start_before = self.start - datetime.timedelta(minutes=2)
        self.start_inside = self.start + datetime.timedelta(minutes=2)
        self.end_inside = self.end - datetime.timedelta(minutes=2)
        self.end_after = self.end + datetime.timedelta(minutes=2)

    #helper functions
    def use_checkoverlap(self, entries):
        """
        Uses entry.check_overlap given a list of entries returns all overlaps
        """
        user_total_overlaps = 0
        for index_a, entry_a in enumerate(entries):
            for index_b in xrange(index_a, len(entries)):
                entry_b = entries[index_b]
                if entry_a.check_overlap(entry_b):
                    user_total_overlaps += 1
        return user_total_overlaps

    def get_entries(self):
        return timepiece.Entry.objects.filter(user=self.user)

    #Invalid entries to test against
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


class CreateEditEntry(TimepieceDataTestCase):
    def setUp(self):
        super(CreateEditEntry, self).setUp()
        self.client.login(username='user', password='abc')
        self.now = datetime.datetime.now()
        valid_start = self.now - datetime.timedelta(days=1)
        valid_end = valid_start + datetime.timedelta(hours=1)
        two_hour_ago = self.now - datetime.timedelta(hours=2)
        one_hour_ago = self.now - datetime.timedelta(hours=1)
        ten_min_ago = self.now - datetime.timedelta(minutes=10)
        #establish data, entries, urls for all tests
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
            'start_time': two_hour_ago,
            'end_time': one_hour_ago,
        }
        self.current_entry_data = {
            'user': self.user,
            'project': self.project,
            'activity': self.devl_activity,
            'start_time': ten_min_ago,
        }
        self.closed_entry = self.create_entry(self.closed_entry_data)
        self.current_entry = self.create_entry(self.current_entry_data)
        self.closed_entry_data.update({
            'st_str': two_hour_ago.strftime('%H:%M:%S'),
            'end_str': one_hour_ago.strftime('%H:%M:%S'),
        })
        self.current_entry_data.update({
            'st_str': ten_min_ago.strftime('%H:%M:%S'),
        })
        self.create_url = reverse('timepiece-add')
        self.edit_closed_url = reverse('timepiece-update',
            args=[self.closed_entry.pk])
        self.edit_current_url = reverse('timepiece-update',
            args=[self.current_entry.pk])

    def testCreateEntry(self):
        """
        Test the ability to create a valid new entry
        """
        response = self.client.post(self.create_url, self.default_data,
            follow=True)
        self.assertRedirects(response, reverse('timepiece-entries'),
            status_code=302, target_status_code=200)
        self.assertContains(response,
            'The entry has been created successfully', count=1)
        #If after Monday, there is one entry this week, otherwise 1
        this_w = 2 if self.now.isoweekday() != 1 else 1
        self.assertEquals(len(response.context['this_weeks_entries']), this_w)

    def testEditClosed(self):
        """
        Test the ability to edit a closed entry, using valid values
        """
        response = self.client.post(self.edit_closed_url, self.default_data,
            follow=True)
        self.assertRedirects(response, reverse('timepiece-entries'),
            status_code=302, target_status_code=200)
        self.assertContains(response,
            'The entry has been updated successfully', count=1)
        #If after Monday, there are two entries this week, otherwise 0
        this_w = 1 if self.now.isoweekday() != 1 else 0
        self.assertEquals(len(response.context['this_weeks_entries']), this_w)

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
        #This post should redirect to the dashboard, with the correct message
        #and 1 active entry, because we updated the current entry from setUp
        self.assertRedirects(response, reverse('timepiece-entries'),
            status_code=302, target_status_code=200)
        self.assertContains(response,
            'The entry has been updated successfully', count=1)
        self.assertEquals(len(response.context['my_active_entries']), 1)

    def testEditCurrentDiffTime(self):
        """
        Test the ability to edit a current entry, using valid new values
        """
        data = self.default_data
        new_start = self.current_entry_data['start_time'] + \
            datetime.timedelta(minutes=5)
        data.update({
            'start_time_0': new_start.strftime('%m/%d/%Y'),
            'start_time_1': new_start.strftime('%H:%M:%S'),
        })
        response = self.client.post(self.edit_current_url, data, follow=True)
        #This post should redirect to the dashboard, with the correct message
        #and 1 active entry, because we updated the current entry from setUp
        self.assertRedirects(response, reverse('timepiece-entries'),
            status_code=302, target_status_code=200)
        self.assertContains(response,
            'The entry has been updated successfully', count=1)
        self.assertEquals(len(response.context['my_active_entries']), 1)

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
        response = self.client.post(self.create_url, overlap_entry,
            follow=True)
        self.assertFormError(response, 'form', None, \
            'Start time overlaps with: ' + \
            '%(project)s - %(activity)s - from %(st_str)s to %(end_str)s' % \
            self.closed_entry_data)

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
        response = self.client.post(self.create_url, overlap_entry,
            follow=True)
        self.assertFormError(response, 'form', None, \
            'The times below conflict with the current entry: ' + \
            '%(project)s - %(activity)s starting at %(st_str)s' % \
            self.current_entry_data)

    def testProjectList(self):
        """
        Make sure the list of available projects conforms to user associations
        """
        response = self.client.get(reverse('timepiece-add'))
        self.assertEqual(response.status_code, 200)
        projects = list(response.context['form'].fields['project'].queryset)
        self.assertTrue(self.project in projects)
        self.assertFalse(self.project2 in projects)

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


class StatusTest(TimepieceDataTestCase):
    def setUp(self):
        super(StatusTest, self).setUp()
        self.create_person_repeat_period(data={'user': self.user})
        period = timepiece.PersonRepeatPeriod.objects.get(user=self.user)
        self.billing_window = timepiece.BillingWindow.objects.create(
            period=period.repeat_period,
            date=datetime.datetime.now(),
            end_date=datetime.datetime.now() + period.repeat_period.delta()
        )
        self.client.login(username='user', password='abc')
        self.sheet_url = reverse('view_person_time_sheet',
            args=[period.user.pk, period.repeat_period.pk,
            self.billing_window.pk])
        self.verify_url = reverse('time_sheet_change_status',
            args=['verify', period.user.pk, period.repeat_period.pk,
            self.billing_window.pk])
        self.approve_url = reverse('time_sheet_change_status',
            args=['approve', period.user.pk, period.repeat_period.pk,
            self.billing_window.pk])

    def testVerifyButton(self):
        response = self.client.get(self.sheet_url)
        self.assertNotContains(response, self.verify_url)
        entry = self.create_entry(data={
            'user': self.user,
            'start_time': datetime.datetime.now() - \
                datetime.timedelta(hours=1),
            'end_time':  datetime.datetime.now(),
        })
        response = self.client.get(self.sheet_url)
        self.assertContains(response, self.verify_url)
        entry.status = 'verified'
        entry.save()
        response = self.client.get(self.sheet_url)
        self.assertNotContains(response, self.verify_url)

    def testApproveButton(self):
        edit_time_sheet = Permission.objects.get(
            codename=('edit_person_time_sheet')
        )
        self.user2.user_permissions.add(edit_time_sheet)
        view_time_sheet = Permission.objects.get(
            codename=('view_person_time_sheet')
        )
        self.user2.user_permissions.add(view_time_sheet)
        self.user2.save()
        self.client.login(username='user2', password='abc')
        response = self.client.get(self.sheet_url)
        self.assertNotContains(response, self.approve_url)
        entry = self.create_entry(data={
            'user': self.user,
            'start_time': datetime.datetime.now() - \
                datetime.timedelta(hours=1),
            'end_time':  datetime.datetime.now(),
        })
        response = self.client.get(self.sheet_url)
        self.assertNotContains(response, self.approve_url)
        entry.status = 'verified'
        entry.save()
        response = self.client.get(self.sheet_url)
        self.assertContains(response, self.approve_url)
        entry.status = 'approved'
        entry.save()
        response = self.client.get(self.sheet_url)
        self.assertNotContains(response, self.approve_url)

    def testVerifyPage(self):
        entry = self.create_entry(data={
            'user': self.user,
            'start_time': datetime.datetime.now() - \
                datetime.timedelta(hours=1),
            'end_time':  datetime.datetime.now(),
        })
        response = self.client.get(self.verify_url)
        entries = self.user.timepiece_entries.all()
        self.assertEquals(entries[0].status, 'unverified')
        response = self.client.post(self.verify_url, {'do_action': 'Yes'})
        self.assertEquals(entries[0].status, 'verified')

    def testApprovePage(self):
        edit_time_sheet = Permission.objects.get(
            codename=('edit_person_time_sheet')
        )
        self.user2.user_permissions.add(edit_time_sheet)
        view_time_sheet = Permission.objects.get(
            codename=('view_person_time_sheet')
        )
        self.user2.user_permissions.add(view_time_sheet)
        self.user2.save()
        self.client.login(username='user2', password='abc')

        entry = self.create_entry(data={
            'user': self.user,
            'start_time': datetime.datetime.now() - \
                datetime.timedelta(hours=1),
            'end_time':  datetime.datetime.now(),
        })
        response = self.client.post(self.approve_url, {'do_action': 'Yes'})
        entries = self.user.timepiece_entries.all()
        self.assertEquals(entries[0].status, 'unverified')
        entry.status = 'verified'
        entry.save()

        response = self.client.get(self.approve_url,)
        entries = self.user.timepiece_entries.all()
        self.assertEquals(entries[0].status, 'verified')

        response = self.client.post(self.approve_url, {'do_action': 'Yes'})
        self.assertEquals(entries[0].status, 'approved')

    def testNotAllowedToAproveTimesheet(self):
        response = self.client.get(self.approve_url,)
        self.assertTrue(response.status_code, 403)

    def testNotAllowedToVerifyTimesheet(self):
        self.client.login(username='user2', password='abc')
        response = self.client.get(self.approve_url,)
        self.assertTrue(response.status_code, 403)


class TestTotals(TimepieceDataTestCase):
    def setUp(self):
        super(TestTotals, self).setUp()
        self.create_person_repeat_period(data={'user': self.user})
        self.p1 = self.create_project(billable=True, name='1')
        self.p2 = self.create_project(billable=False, name='2')
        self.p4 = self.create_project(billable=True, name='4')
        #For use with daily totals (Same project, non-billable activity)
        self.p3 = self.create_project(billable=False, name='1')

        period = timepiece.PersonRepeatPeriod.objects.get(user=self.user)
        self.billing_window = timepiece.BillingWindow.objects.create(
            period=period.repeat_period,
            date=datetime.datetime(2010, 12, 1),
            end_date=datetime.datetime(2011, 12, 1),
        )
        self.client.login(username='user', password='abc')
        self.url = reverse('view_person_time_sheet',
            args=[period.user.pk, period.repeat_period.pk,
            self.billing_window.pk])
        self.hourly_url = reverse('view_person_time_sheet',
            args=[period.user.pk, period.repeat_period.pk,
            self.billing_window.pk, 'hourly'])

    def testGroupedTotals(self):
        self.client.login(username='user', password='abc')
        days = [
                datetime.datetime(2011, 1, 3),
                datetime.datetime(2011, 1, 4),
                datetime.datetime(2011, 1, 10),
                datetime.datetime(2011, 1, 16),
                datetime.datetime(2011, 1, 17),
                datetime.datetime(2011, 1, 18)
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
        self.log_time(project=self.p2, start=days[4], delta=(1, 0))
        self.log_time(project=self.p4, start=days[4], delta=(1, 0))
        self.log_time(project=self.p1, start=days[5], delta=(1, 0))
        self.log_time(project=self.p3, start=days[5], delta=(1, 0))
        self.log_time(project=self.p4, start=days[5], delta=(1, 0))
        entries = timepiece.Entry.objects.all()
        grouped_totals = utils.grouped_totals(entries)
        for week, week_totals, days in grouped_totals:
            #Jan. 3rd is a monday. Each week should be on a monday
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
