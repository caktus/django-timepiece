import time
import datetime
import random
import itertools

from django.core.urlresolvers import reverse

from timepiece.tests.base import BaseTest

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms

from dateutil import relativedelta


class ClockInTest(BaseTest):
    def setUp(self):
        super(ClockInTest, self).setUp()
        self.url = reverse('timepiece-clock-in')
    
    def testClockInLogin(self):
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 302)
        self.client.login(username='user', password='abc')
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)
    
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


class ClockOutTest(BaseTest):
    def setUp(self):
        super(ClockOutTest, self).setUp()
    
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
        response = self.client.post(reverse('timepiece-clock-out', args=[entry.pk]), data, follow=True)
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


def previous_and_next(some_iterable):
    prevs, items, nexts = itertools.tee(some_iterable, 3)
    prevs = itertools.chain([None], prevs)
    nexts = itertools.chain(itertools.islice(nexts, 1, None), [None])
    return itertools.izip(prevs, items, nexts)


class BillingPeriodTest(BaseTest):
    def assertWindowBoundaries(self, windows):
        for prev, curr, next in previous_and_next(windows):
            if curr and prev:
                diff = \
                    relativedelta.relativedelta(curr.date, prev.date)
                self.assertEqual(prev.date + diff, curr.date)
                self.assertEqual(prev.end_date, curr.date)
    
    def testGeneratedWindows(self):
        delta = relativedelta.relativedelta(days=random.randint(20, 100))
        start_date = datetime.datetime.today() - delta
        for count in range(1, 30):
            for period, _ in timepiece.RepeatPeriod.INTERVAL_CHOICES:
                p = timepiece.RepeatPeriod.objects.create(
                    count=2,
                    interval='week',
                    active=True,
                )
                self.project.billing_period = p
                self.project.save()
                window = p.billing_windows.create(
                    date=start_date,
                    end_date=start_date + p.delta(),
                )
                p.update_billing_windows()
                windows = p.billing_windows.order_by('date')
                self.assertWindowBoundaries(windows)
                p.delete()
    
    
    def testChangedPeriod(self):
        """
        If an existing period is updated with a new delta, check that
        no time windows are missed when the new delta is applied.
        """
        start_date = datetime.date(2009, 9, 4)
        p = timepiece.RepeatPeriod.objects.create(
            count=2,
            interval='week',
            active=True,
        )
        self.project.billing_period = p
        self.project.save()
        window = p.billing_windows.create(
            date=start_date,
            end_date=start_date + p.delta(),
        )
        p.count = 1
        p.interval = 'month'
        p.save()
        p.update_billing_windows(date_boundary=datetime.date(2009, 10, 17))
        windows = p.billing_windows.order_by('date')
        self.assertWindowBoundaries(windows)
        self.assertEqual(len(windows), 2)
    
    def testChangedStartDate(self):
        start_date = datetime.date(2009, 9, 4)
        p = timepiece.RepeatPeriod.objects.create(
            count=2,
            interval='week',
            active=True,
        )
        self.project.billing_period = p
        self.project.save()
        window = p.billing_windows.create(
            date=start_date,
            end_date=start_date + p.delta(),
        )
        data = {
            'repeat-active': 'on',
            'repeat-count': '1',
            'repeat-interval': 'month',
            'repeat-date': '10/01/2009',
        }
        form = timepiece_forms.RepeatPeriodForm(
            data,
            instance=p,
            prefix='repeat',
        )
        self.assertTrue(form.is_valid())
        p = form.save()
        self.assertWindowBoundaries(p.billing_windows.order_by('date'))
        