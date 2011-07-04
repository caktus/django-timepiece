import time
import datetime
import random
import itertools

from django.core.urlresolvers import reverse

from django.contrib.auth.models import User, Permission

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
        })
        self.entry2 = self.create_entry({
            'user': self.user,
            'project': self.project,
            'start_time': datetime.datetime.now() - datetime.timedelta(days=2),
            'end_time':  datetime.datetime.now() - datetime.timedelta(days=2),
            'seconds_paused': 0,
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


class ClockInTest(TimepieceDataTestCase):
    def setUp(self):
        super(ClockInTest, self).setUp()
        self.url = reverse('timepiece-clock-in')
    
    def testClockInPause(self):
        self.client.login(username='user', password='abc')
        now = datetime.datetime.now()- datetime.timedelta(minutes=20)
        data = {
            'project': self.project.id,
            'start_time_0': now.strftime('%m/%d/%Y'),
            'start_time_1': now.strftime('%H:%M:00'),
        }
        response = self.client.post(self.url, data)
        now = datetime.datetime.now()+ datetime.timedelta(seconds=1)
        data = {
            'project': self.project2.id,
            'start_time_0': now,
            'start_time_1': now,
        }        
        response = self.client.post(self.url, data)
        for entry in timepiece.Entry.objects.all():
            now = datetime.datetime.now()
            data = {
                'end_time_0': now.strftime('%m/%d/%Y'),
                'end_time_1': now.strftime('%H:%M:00'),
            }
            response = self.client.post(
                reverse('timepiece-clock-out', args=[entry.pk]),
                data,
                follow=True,
            )
        for entry in timepiece.Entry.objects.all():
            if entry.is_overlapping() != False:
                self.fail('Overlapping Times')
    
    def testPausePause(self):
        self.client.login(username='user', password='abc')
        now = datetime.datetime.now()- datetime.timedelta(minutes=20)
        data = {
            'project': self.project.id,
            'start_time_0': now.strftime('%m/%d/%Y'),
            'start_time_1': now.strftime('%H:%M:00'),
            'location': self.location.pk,
            'activity': self.devl_activity.pk,
        }
        response = self.client.post(self.url, data)
        e_id = timepiece.Entry.objects.filter(project=self.project.id)[0]
        now = datetime.datetime.now()+ datetime.timedelta(seconds=1)
        data = {
            'project': self.project2.id,
            'start_time_0': now,
            'start_time_1': now,
            'location': self.location.pk,
        }        
        response = self.client.post(self.url, data)
        e_id.unpause()
        for entry in timepiece.Entry.objects.all():
            now = datetime.datetime.now()+datetime.timedelta(hours=1)
            data = {
                'end_time_0': now.strftime('%m/%d/%Y'),
                'end_time_1': now.strftime('%H:%M:00'),
                'location': self.location.pk,
            }
            response = self.client.post(
                reverse('timepiece-clock-out', args=[entry.pk]),
                data,
                follow=True,
            )
        for entry in timepiece.Entry.objects.all():
            if entry.is_overlapping() != False:
                self.fail('Overlapping Times')
    
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
        entry = self.create_entry({
            'user': self.user,
            'project': self.project,
            'start_time': datetime.datetime.now() - datetime.timedelta(hours=5),
        })
        self.client.login(username='user', password='abc')
        now = datetime.datetime.now()
        data = {
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
        entry = self.create_entry({
            'user': self.user,
            'project': self.project,
            'start_time': now - datetime.timedelta(hours=5),
            'seconds_paused': 3600, # 1 hour
        })
        end_time = now - datetime.timedelta(hours=1)
        data = {
            'end_time_0': end_time.strftime('%m/%d/%Y'),
            'end_time_1': end_time.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        form = timepiece_forms.ClockOutForm(data, instance=entry)
        self.assertTrue(form.is_valid())
        saved = form.save()
        self.assertAlmostEqual(saved.hours, 3)
    
    def testClockOutWhilePaused(self):
        now = datetime.datetime.now()
        entry = self.create_entry({
            'user': self.user,
            'project': self.project,
            'start_time': now - datetime.timedelta(hours=5),
            'pause_time': now - datetime.timedelta(hours=4),
        })
        end_time = now - datetime.timedelta(hours=1)
        data = {
            'end_time_0': end_time.strftime('%m/%d/%Y'),
            'end_time_1': end_time.strftime('%H:%M:%S'),
            'location': self.location.pk,
        }
        form = timepiece_forms.ClockOutForm(data, instance=entry)
        self.assertTrue(form.is_valid())
        saved = form.save()
        self.assertAlmostEqual(saved.hours, 1)


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
        self.sheet_url = reverse('view_person_time_sheet', args=[period.user.pk, period.repeat_period.pk])
        self.verify_url = reverse('time_sheet_change_status', args=['verify', period.user.pk, period.repeat_period.pk])
        self.approve_url = reverse('time_sheet_change_status', args=['approve', period.user.pk, period.repeat_period.pk])
    
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
