import time
import datetime
import random
import itertools
from urllib import urlencode

from django.core.urlresolvers import reverse

from django.contrib.auth.models import User, Permission
from django.core.exceptions import ValidationError

from timepiece.tests.base import TimepieceDataTestCase

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms

from dateutil import relativedelta


class EditableTest(TimepieceDataTestCase):
    def setUp(self):
        super(EditableTest, self).setUp()
        self.day_period = timepiece.RepeatPeriod.objects.create(
            count = 2,
            interval = 'day',
            active = True,
        )
        self.timesheet = timepiece.PersonRepeatPeriod.objects.create(
            user = self.user,
            repeat_period = self.day_period
        )
        self.billing_window = timepiece.BillingWindow.objects.create(
            period = self.day_period,
            date = datetime.datetime.now() - datetime.timedelta(days=8),
            end_date = datetime.datetime.now() - datetime.timedelta(days=8) + self.day_period.delta(),
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
            count = 1,
            interval = 'month',
            active = True,
        )
        self.timesheet = timepiece.PersonRepeatPeriod.objects.create(
            user = self.user,
            repeat_period = self.month_period
        )
        self.billing_window = timepiece.BillingWindow.objects.create(
            period = self.month_period,
            date = datetime.datetime.now(),
            end_date = datetime.datetime.now() + self.month_period.delta()
        )
        self.url = reverse('view_person_time_sheet', kwargs={
            'person_id': self.user.pk,
            'period_id': self.timesheet.repeat_period.pk,
        })

    def testMyLedger(self):
        self.client.login(username='user', password='abc')
        response = self.client.get(self.url)
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
            
    def testMyLedgerWeeklyTotals(self):
        """
        Check the accuracy of the weekly hours summary
        """
        self.user.is_staff = True
        self.user.save()        
        self.client.login(username=self.user.username, password='abc')
        now = datetime.datetime.now() - datetime.timedelta(hours=10)
        backthen = now - datetime.timedelta(hours=20)        
        #create a billable and non-billable entry for testing
        project_billable = self.create_project(billable=True)
        project_non_billable = self.create_project(billable=False)
        entry1 = self.create_entry({
            'user': self.user,
            'project': project_billable,
            'start_time': backthen,
            'end_time': now,
        })
        entry2 = self.create_entry({
            'user': self.user,
            'project': project_non_billable,
            'start_time': entry1.start_time + datetime.timedelta(hours=11),
            'end_time': entry1.end_time + datetime.timedelta(hours=15),
        })         
        url = reverse('view_person_time_sheet', kwargs = {
            'person_id': self.user.pk,
            'period_id': self.timesheet.repeat_period.pk
        })
        response = self.client.get(url)       
        weekly_entries = response.context['weekly_entries']
        #Check that the flag for showing "week of dd/mm/yyyy" is set correctly
        self.assertEqual(weekly_entries[0][1], 1)
        self.assertEqual(weekly_entries[1][1], 0)
        #Check that the totals returned are correct and in the correct place
        self.assertEqual(weekly_entries[1][2][0], 20.00)
        self.assertEqual(weekly_entries[1][2][1], 24.00)
        self.assertEqual(weekly_entries[1][2][2], 44.00)
    
    def testMyLedgerRedirect(self):
        """
        Check that editing an entry redirects to "My Ledger" not the dashboard.
        """
        self.user.is_staff = True
        self.user.save()
        self.client.login(username=self.user.username, password='abc')
        now = datetime.datetime.now() - datetime.timedelta(hours=10)
        backthen = now - datetime.timedelta(hours=20)        
        project_billable = self.create_project(billable=True)
        entry1 = self.create_entry({
            'user': self.user,
            'project': project_billable,
            'start_time': backthen,
            'end_time': now,
        })
        my_ledger_url = reverse('view_person_time_sheet', kwargs ={
            'person_id': self.user.pk,
            'period_id': self.timesheet.repeat_period.pk
        })
        edit_entry_url = reverse('timepiece-update', kwargs ={
            'entry_id': entry1.id,
        })
        get_str = '?%s' % urlencode({
            'next': my_ledger_url,
        })
        data = {
            'project': self.project.id,
            'activity': self.activity.id,
            'location': self.location.id,
            'start_time_0': entry1.start_time.strftime('%m/%d/%Y'),
            'start_time_1': entry1.start_time.strftime('%H:%M:00'),
            'end_time_0': entry1.end_time.strftime('%m/%d/%Y'),
            'end_time_1': entry1.end_time.strftime('%H:%M:00'),
            'seconds_paused': 0,   
        }
        response = self.client.post(edit_entry_url + get_str, data, follow=True)
        self.assertEqual(response.request['PATH_INFO'], my_ledger_url)


class ClockInTest(TimepieceDataTestCase):
    def setUp(self):
        super(ClockInTest, self).setUp()
        self.url = reverse('timepiece-clock-in')
    
    def testClockIn(self):
        self.client.login(username='user', password='abc')
        now = datetime.datetime.now()- datetime.timedelta(minutes=20)
        data = {
            'project': self.project.id,
            'start_time_0': now.strftime('%m/%d/%Y'),
            'start_time_1': now.strftime('%H:%M:00'),
        }
        response = self.client.post(self.url, data)
        now = datetime.datetime.now() - datetime.timedelta(seconds=1)
        data = {
            'project': self.project2.id,
            'start_time_0': now,
            'start_time_1': now,
        }        
        response = self.client.post(self.url, data)
        #clock out calls removed from tests. Clock in view clocks out active entries automatically
        for entry in timepiece.Entry.objects.all():
            if entry.is_overlapping() != False:
                self.fail('Overlapping Times')
                
    def testClockInPause(self):
        self.client.login(username='user', password='abc')
        now = datetime.datetime.now()- datetime.timedelta(minutes=10)
        data = {
            'project': self.project.id,
            'start_time_0': now.strftime('%m/%d/%Y'),
            'start_time_1': now.strftime('%H:%M:00'),
            'location': self.location.pk,
            'activity': self.devl_activity.pk,
        }
        response = self.client.post(self.url, data)
        e_id = timepiece.Entry.objects.filter(project=self.project.id)[0]
        e_id.pause()#check that when the first entry is paused, the second clock in works and clocks out the first
        now = datetime.datetime.now()
        data = {
            'project': self.project2.id,
            'start_time_0': now.strftime('%m/%d/%Y'),
            'start_time_1': now.strftime('%H:%M:00'),
            'location': self.location.pk,
            'activity': self.devl_activity.pk,
        }        
        response = self.client.post(self.url, data)
        for entry in timepiece.Entry.objects.all():
            if entry.is_overlapping():            
                self.fail('Overlapping Times') 
                
    def testClockInBlock(self):        
        """
        Guarantee that the user cannot clock in to a time that is already logged        
        """        
        now = datetime.datetime.now()
        entry = self.create_entry({
            'user': self.user,
            'project': self.project,
            'start_time': now - datetime.timedelta(hours=5),
            'end_time': now,
        })
        conflicting_start_time = entry.start_time + datetime.timedelta(hours=2)
        data = {
            'start_time_0': conflicting_start_time.strftime('%m/%d/%Y'),
            'start_time_1': conflicting_start_time.strftime('%H:%M:00'),
            'location': entry.location.pk,
            'project': entry.project.pk,
            'activity': entry.activity.pk,
        }
        
        #This clock in attempt should be blocked by the last entry
        entry = timepiece.Entry(user=self.user)
        form = timepiece_forms.ClockInForm(data, instance=entry, user=self.user)
        self.assertIs(form.is_valid(), False)
    
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
        data = {
            'project': self.project2.id,
            'start_time_0': [u'11/02/2009'],
            'start_time_1': [u'11:09:21'],
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
    
    def testClockIn(self):
        self.client.login(username='user', password='abc')
        data = {
            'project': self.project.id,
            'start_time_0': [u'11/02/2009'],
            'start_time_1': [u'11:09:21'],
            'location': self.location.pk,
            'activity': self.devl_activity.pk,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(timepiece.Entry.objects.count(), 1)
        


class ClockOutTest(TimepieceDataTestCase):
    def testBasicClockOut(self):
        now = datetime.datetime.now()
        backthen = now - datetime.timedelta(hours=5)
        entry = self.create_entry({
            'user': self.user,
            'project': self.project,
            'start_time': backthen,
        })
        self.client.login(username='user', password='abc')        
        data = {
            'start_time_0': backthen.strftime('%m/%d/%Y'),
            'start_time_1': backthen.strftime('%H:%M:00'),
            'end_time_0': now.strftime('%m/%d/%Y'),
            'end_time_1': now.strftime('%H:%M:00'),
            'location': self.location.pk,
        }
        response = self.client.post(
            reverse('timepiece-clock-out', args=[entry.pk]),
            data,
            follow=True,
        )
        entry = timepiece.Entry.objects.get(pk=entry.pk)
        self.assertTrue(entry.is_closed)
    
    def testClockOutWithSecondsPaused(self):
        now = datetime.datetime.now()
        backthen = now - datetime.timedelta(hours=4)
        entry = self.create_entry({
            'user': self.user,
            'project': self.project,
            'start_time': backthen,
            'seconds_paused': 3600, # 1 hour
        })
        data = {
            'start_time_0': backthen.strftime('%m/%d/%Y'),
            'start_time_1': backthen.strftime('%H:%M:%S'),
            'end_time_0': now.strftime('%m/%d/%Y'),
            'end_time_1': now.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        form = timepiece_forms.ClockOutForm(data, instance=entry)
        self.assertTrue(form.is_valid())
        saved = form.save()
        self.assertAlmostEqual(saved.hours, 3)
    
    def testClockOutWhilePaused(self):
        now = datetime.datetime.now()
        backthen = now - datetime.timedelta(hours=3)
        entry = self.create_entry({
            'user': self.user,
            'project': self.project,
            'start_time': backthen,
            'pause_time': now - datetime.timedelta(hours=1),
        })

        data = {
            'start_time_0': backthen.strftime('%m/%d/%Y'),
            'start_time_1': backthen.strftime('%H:%M:%S'),
            'end_time_0': now.strftime('%m/%d/%Y'),
            'end_time_1': now.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        form = timepiece_forms.ClockOutForm(data, instance=entry)
        self.assertTrue(form.is_valid())
        saved = form.save()
        self.assertAlmostEqual(saved.hours, 2)
        
    def testClockOutReverse(self):
        """Test that the user can't clock out at a time prior to the starting 
        time
        """
        now = datetime.datetime.now()
        backthen = now - datetime.timedelta(hours=3)        
        backward_entry = self.create_entry({
            'user': self.user,
            'project': self.project,
            'start_time': now,
        })        
        data = {
            'start_time_0': backward_entry.start_time.strftime('%m/%d/%Y'),
            'start_time_1': backward_entry.start_time.strftime('%H:%M:%S'),
            'end_time_0': backthen.strftime('%m/%d/%Y'),
            'end_time_1': backthen.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        form = timepiece_forms.ClockOutForm(data, instance=backward_entry)
        self.assertFalse(form.is_valid())
    
    def testClockOutOverlap(self):
        """Test that the user cannot clock out if the times overlap with an
        existing entry
        """
        now = datetime.datetime.now()
        backthen = now - datetime.timedelta(hours=8)
        existing_entry = self.create_entry({
            'user': self.user,
            'start_time': backthen,
            'end_time': now,
        })
        new_entry_start_time = existing_entry.start_time + datetime.timedelta(hours=1)
        new_entry_end_time = now - datetime.timedelta(hours=1)
        data = {
            'start_time_0': new_entry_start_time.strftime('%m/%d/%Y'),
            'start_time_1': new_entry_start_time.strftime('%H:%M:%S'),
            'end_time_0': new_entry_end_time.strftime('%m/%d/%Y'),
            'end_time_1': new_entry_end_time.strftime('%H:%M:%S'),
            'location': self.location.pk,        
        }
        #With the existing_entry on either side, a form with the information in
        #data should fail as the times are inside the times of a previous entry
        existing_entry = timepiece.Entry(user=self.user)
        form = timepiece_forms.ClockOutForm(data, instance=existing_entry)
        self.assertFalse(form.is_valid())

class CreateEditEntry(TimepieceDataTestCase):
    def testProjectList(self):
        self.client.login(username='user', password='abc')
        response = self.client.get(reverse('timepiece-add'))
        self.assertEqual(response.status_code, 200)
        projects = list(response.context['form'].fields['project'].queryset)
        self.assertTrue(self.project in projects)
        self.assertFalse(self.project2 in projects)
        
        
class StatusTest(TimepieceDataTestCase):
    def setUp(self):
        super(StatusTest, self).setUp()
        self.create_person_repeat_period(data={'user': self.user})
        period = timepiece.PersonRepeatPeriod.objects.get(user=self.user)
        self.billing_window = timepiece.BillingWindow.objects.create(
            period = period.repeat_period,
            date = datetime.datetime.now(),
            end_date = datetime.datetime.now() + period.repeat_period.delta()
        )
        self.client.login(username='user', password='abc')
        self.sheet_url = reverse('view_person_time_sheet', args=[period.user.pk, period.repeat_period.pk, self.billing_window.pk])
        self.verify_url = reverse('time_sheet_change_status', args=['verify', period.user.pk, period.repeat_period.pk, self.billing_window.pk])
        self.approve_url = reverse('time_sheet_change_status', args=['approve', period.user.pk, period.repeat_period.pk, self.billing_window.pk])
    
    def testVerifyButton(self):
        response = self.client.get(self.sheet_url)        
        self.assertNotContains(response, self.verify_url)
        entry = self.create_entry(data={
            'user': self.user, 
            'start_time': datetime.datetime.now() - datetime.timedelta(hours=1),
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
            'start_time': datetime.datetime.now() - datetime.timedelta(hours=1),
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
            'start_time': datetime.datetime.now() - datetime.timedelta(hours=1),
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
            'start_time': datetime.datetime.now() - datetime.timedelta(hours=1),
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
