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
        tz = timezone.get_current_timezone()
        self.last_billable = [
            datetime.datetime(2012, 3, 25, tzinfo=tz),
            datetime.datetime(2012, 4, 29, tzinfo=tz),
            datetime.datetime(2012, 5, 27, tzinfo=tz),
            datetime.datetime(2012, 6, 24, tzinfo=tz),
            datetime.datetime(2012, 7, 29, tzinfo=tz),
            datetime.datetime(2012, 8, 26, tzinfo=tz),
        ]
        self.dates = [
            datetime.datetime(2012, 3, 12, tzinfo=tz),
            datetime.datetime(2012, 4, 3, tzinfo=tz),
            datetime.datetime(2012, 5, 18, tzinfo=tz),
            datetime.datetime(2012, 6, 20, tzinfo=tz),
            datetime.datetime(2012, 7, 1, tzinfo=tz),
            datetime.datetime(2012, 8, 25, tzinfo=tz),
        ]

    def test_get_last_billable_day(self):
        for idx, date in enumerate(self.dates):
            self.assertEquals(self.last_billable[idx],
                utils.get_last_billable_day(date))
