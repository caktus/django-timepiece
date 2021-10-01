import datetime
from decimal import Decimal

from django.test import TestCase
from timepiece.utils import get_active_entry, ActiveEntryError
from timepiece.utils.views import format_totals
from timepiece import utils

from . import factories


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
            self.assertEquals(
                self.last_billable[idx], utils.get_last_billable_day(date))


class GetActiveEntryTest(TestCase):

    def setUp(self):
        self.user = factories.User()

    def test_get_active_entry_none(self):
        self.assertIsNone(get_active_entry(self.user))

    def test_get_active_entry_single(self):
        now = datetime.datetime.now()
        entry = factories.Entry(user=self.user, start_time=now)
        # not active
        factories.Entry(
            user=self.user, start_time=now, end_time=now)
        # different user
        factories.Entry(start_time=now)
        self.assertEqual(entry, get_active_entry(self.user))

    def test_get_active_entry_multiple(self):
        now = datetime.datetime.now()
        # two active entries for same user
        factories.Entry(user=self.user, start_time=now)
        factories.Entry(user=self.user, start_time=now)
        self.assertRaises(ActiveEntryError, get_active_entry, self.user)


class FormatTotalsTest(TestCase):

    def test_default_format_totals(self):
        entries = [
            {'sum': Decimal('60.50000'), 'user__first_name': 'Rob', 'user__last_name': 'Lin'},
            {'sum': Decimal('30.75000'), 'user__first_name': 'Dave', 'user__last_name': 'Roy'},
            {'sum': Decimal('20.20500'), 'user__first_name': 'Mike', 'user__last_name': 'Jones'},
            ]
        format_totals(entries)
        self.assertEqual(entries[0]['sum'], "{0:.2f}".format(60.50))
        self.assertEqual(entries[1]['sum'], "{0:.2f}".format(30.75))
        self.assertEqual(entries[2]['sum'], "{0:.2f}".format(20.20))

    def test_format_totals_with_param(self):
        entries = [
            {'smurf': Decimal('60.50000'), 'user__first_name': 'Rob', 'user__last_name': 'Lin'},
            {'smurf': Decimal('30.75000'), 'user__first_name': 'Dave', 'user__last_name': 'Roy'},
            {'smurf': Decimal('20.20500'), 'user__first_name': 'Mike', 'user__last_name': 'Jones'},
            ]
        format_totals(entries, 'smurf')
        self.assertEqual(entries[0]['smurf'], "{0:.2f}".format(60.50))
        self.assertEqual(entries[1]['smurf'], "{0:.2f}".format(30.75))
        self.assertEqual(entries[2]['smurf'], "{0:.2f}".format(20.20))
