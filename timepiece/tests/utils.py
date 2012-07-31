import datetime

from django.test import TestCase

try:
    from django.utils import timezone
except ImportError:
    from timepiece import timezone

from timepiece import utils


class UtilityFunctionsTest(TestCase):
    def setUp(self):
        # Setup last billable days
        self.last_billable = [
            utils.add_timezone(datetime.datetime(2012, 3, 25)),
            utils.add_timezone(datetime.datetime(2012, 4, 29)),
            utils.add_timezone(datetime.datetime(2012, 5, 27)),
            utils.add_timezone(datetime.datetime(2012, 6, 24)),
            utils.add_timezone(datetime.datetime(2012, 7, 29)),
            utils.add_timezone(datetime.datetime(2012, 8, 26)),
        ]
        self.dates = [
            utils.add_timezone(datetime.datetime(2012, 3, 12)),
            utils.add_timezone(datetime.datetime(2012, 4, 3)),
            utils.add_timezone(datetime.datetime(2012, 5, 18)),
            utils.add_timezone(datetime.datetime(2012, 6, 20)),
            utils.add_timezone(datetime.datetime(2012, 7, 1)),
            utils.add_timezone(datetime.datetime(2012, 8, 25)),
        ]

    def test_get_last_billable_day(self):
        for idx, date in enumerate(self.dates):
            self.assertEquals(self.last_billable[idx],
                utils.get_last_billable_day(date))
