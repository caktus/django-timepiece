from django.test import TestCase
from django.test.client import Client
from pendulum.utils import determine_period
from datetime import datetime

class DetermineDatesTestCase(TestCase):
    """
    Make sure the period date boundary function is working properly.  Currently
    the range calculator will go from the first day of the month to the last
    day of the same month.  Eventually, this should test for configurable
    period lengths.
    """

    fixtures = ['activities', 'projects', 'users', 'entries']

    def setUp(self):
        self.client = Client()

    def testDeterminePeriod(self):
        # try some dates
        dates_to_try = (
            datetime(2005, 12, 13), datetime(2006, 4, 12),
            datetime(2006, 7, 19),  datetime(2007, 1, 9),
            datetime(2007, 5, 21),  datetime(2007, 6, 10),
            datetime(2007, 6, 26),  datetime(2007, 7, 2),
            datetime(2007, 7, 31),  datetime(2007, 9, 6),
            datetime(2007, 12, 2),  datetime(2008, 1, 30),
            datetime(2008, 2, 27),  datetime(2008, 6, 6),
        )

        expected_results = [
            (datetime(2005, 12, 1), datetime(2005, 12, 31)),    # 13 dec 05
            (datetime(2006, 4, 1), datetime(2006, 4, 30)),      # 12 apr 06
            (datetime(2006, 7, 1), datetime(2006, 7, 31)),      # 19 jul 06
            (datetime(2007, 1, 1), datetime(2007, 1, 31)),      # 9 jan 07
            (datetime(2007, 5, 1), datetime(2007, 5, 31)),      # 21 may 07
            (datetime(2007, 6, 1), datetime(2007, 6, 30)),      # 10 jun 07
            (datetime(2007, 6, 1), datetime(2007, 6, 30)),      # 26 jun 07
            (datetime(2007, 7, 1), datetime(2007, 7, 31)),      # 2 jul 07
            (datetime(2007, 7, 1), datetime(2007, 7, 31)),      # 31 jul 07
            (datetime(2007, 9, 1), datetime(2007, 9, 30)),      # 6 sept 07
            (datetime(2007, 12, 1), datetime(2007, 12, 31)),    # 2 dec 07
            (datetime(2008, 1, 1), datetime(2008, 1, 31)),      # 30 jan 08
            (datetime(2008, 2, 1), datetime(2008, 2, 29)),      # 27 feb 08
            (datetime(2008, 6, 1), datetime(2008, 6, 30)),      # 6 jun 08
        ]

        count = 0
        for date in dates_to_try:
            start, end = determine_period(date)

            exp_s, exp_e = expected_results[count]

            # make sure the resulting start date matches the expected value
            self.assertEquals(start.year, exp_s.year)
            self.assertEquals(start.month, exp_s.month)
            self.assertEquals(start.day, exp_s.day)

            # make sure the resulting end date matches the expected value
            self.assertEquals(end.year, exp_e.year)
            self.assertEquals(end.month, exp_e.month)
            self.assertEquals(end.day, exp_e.day)

            # increment the counter so we can get the correct expected results
            count += 1
