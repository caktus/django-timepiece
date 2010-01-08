import time
import datetime
import random
import itertools

from django.core.urlresolvers import reverse

from timepiece.tests.base import TimepieceDataTestCase

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms

from dateutil import relativedelta


class MyLedgerTest(TimepieceDataTestCase):
    def setUp(self):
        super(MyLedgerTest, self).setUp()
        self.month_period = timepiece.RepeatPeriod.objects.create(
            count = 1,
            interval = 'month',
            active = True,
        )
        self.timesheet = timepiece.PersonRepeatPeriod.objects.create(
            contact = self.contact,
            repeat_period = self.month_period
        )
        self.billing_window = timepiece.BillingWindow.objects.create(
            period = self.month_period,
            date = datetime.datetime.now(),
            end_date = datetime.datetime.now() + self.month_period.delta()
        )
        self.url = reverse('view_person_time_sheet', \
        kwargs={'person_id': self.contact.pk, 'period_id': self.timesheet.pk})

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
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(timepiece.Entry.objects.count(), 1)


class ClockOutTest(TimepieceDataTestCase):
    def testBasicClockOut(self):
        entry = timepiece.Entry.objects.create(
            user=self.user,
            project=self.project,
            activity=self.activity,
            start_time=datetime.datetime.now() - datetime.timedelta(hours=5),
        )
        self.client.login(username='user', password='abc')
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
        entry = timepiece.Entry.objects.get(pk=entry.pk)
        self.assertTrue(entry.is_closed)
    
    def testClockOutWithSecondsPaused(self):
        now = datetime.datetime.now()
        entry = timepiece.Entry.objects.create(
            user=self.user,
            project=self.project,
            activity=self.activity,
            start_time=now - datetime.timedelta(hours=5),
            seconds_paused=3600, # 1 hour
        )
        end_time = now - datetime.timedelta(hours=1)
        data = {
            'end_time_0': end_time.strftime('%m/%d/%Y'),
            'end_time_1': end_time.strftime('%H:%M:%S'),
        }
        form = timepiece_forms.ClockOutForm(data, instance=entry)
        self.assertTrue(form.is_valid())
        saved = form.save()
        self.assertAlmostEqual(saved.hours, 3)
    
    def testClockOutWhilePaused(self):
        now = datetime.datetime.now()
        entry = timepiece.Entry.objects.create(
            user=self.user,
            project=self.project,
            activity=self.activity,
            start_time=now - datetime.timedelta(hours=5),
            pause_time=now - datetime.timedelta(hours=4)
        )
        end_time = now - datetime.timedelta(hours=1)
        data = {
            'end_time_0': end_time.strftime('%m/%d/%Y'),
            'end_time_1': end_time.strftime('%H:%M:%S'),
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
