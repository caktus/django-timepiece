import datetime

from django.test import TestCase
from timepiece.utils import get_active_entry, ActiveEntryError
from django.utils import timezone

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
            self.assertEquals(self.last_billable[idx],
                utils.get_last_billable_day(date))


class GetActiveEntryTest(TestCase):

    def setUp(self):
        self.user = factories.UserFactory()

    def test_get_active_entry_none(self):
        self.assertIsNone(get_active_entry(self.user))

    def test_get_active_entry_single(self):
        now = datetime.datetime.now()
        entry = factories.EntryFactory(user=self.user, start_time=now)
        # not active
        factories.EntryFactory(user=self.user, start_time=now,
                end_time=now)
        # different user
        factories.EntryFactory(start_time=now)
        self.assertEqual(entry, get_active_entry(self.user))

    def test_get_active_entry_multiple(self):
        now = datetime.datetime.now()
        # two active entries for same user
        factories.EntryFactory(user=self.user, start_time=now)
        factories.EntryFactory(user=self.user, start_time=now)
        self.assertRaises(ActiveEntryError, get_active_entry, self.user)
