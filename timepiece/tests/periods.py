import time
import datetime
import random
import itertools

from django.core.urlresolvers import reverse

from timepiece.tests.base import TimepieceDataTestCase

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms

from dateutil import relativedelta


def previous_and_next(some_iterable):
    prevs, items, nexts = itertools.tee(some_iterable, 3)
    prevs = itertools.chain([None], prevs)
    nexts = itertools.chain(itertools.islice(nexts, 1, None), [None])
    return itertools.izip(prevs, items, nexts)


class BillingPeriodTest(TimepieceDataTestCase):
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
