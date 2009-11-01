import time
import datetime
import random
import itertools

from django.core.urlresolvers import reverse

from timepiece.tests.base import BaseTest

from timepiece import models as timepiece

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
        response = self.client.post(self.url, {'project': self.project.id})
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
        self.client.post(reverse('timepiece-clock-out', args=[entry.pk]))
        entry = timepiece.Entry.objects.get(pk=entry.pk)
        self.assertTrue(entry.is_closed)


def previous_and_next(some_iterable):
    prevs, items, nexts = itertools.tee(some_iterable, 3)
    prevs = itertools.chain([None], prevs)
    nexts = itertools.chain(itertools.islice(nexts, 1, None), [None])
    return itertools.izip(prevs, items, nexts)


class BillingPeriodTest(BaseTest):
    def checkWindowBoundaries(self, windows):
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
                p = self.project.billing_periods.create(
                    count=count,
                    interval=period,
                    active=True,
                )
                window = p.billing_windows.create(
                    date=start_date,
                    end_date=start_date + p.delta(),
                )
                p.update_billing_windows()
                windows = p.billing_windows.order_by('date')
                self.checkWindowBoundaries(windows)
                p.delete()
    
    
    def testChangedPeriod(self):
        """
        If an existing period is updated with a new delta, check that
        no time windows are missed when the new delta is applied.
        """
        start_date = datetime.date(2009, 9, 4)
        p = self.project.billing_periods.create(
            count=2,
            interval='week',
            active=True,
        )
        window = p.billing_windows.create(
            date=start_date,
            end_date=start_date + p.delta(),
        )
        p.count = 1
        p.interval = 'month'
        p.save()
        p.update_billing_windows()
        windows = p.billing_windows.order_by('date')
        self.checkWindowBoundaries(windows)
        