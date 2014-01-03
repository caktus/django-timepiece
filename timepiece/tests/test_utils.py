import datetime

from django.test import TestCase
from timepiece.utils import get_active_entry, ActiveEntryError

from timepiece import utils
from timepiece.utils.models import Constants

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
        self.user = factories.User()

    def test_get_active_entry_none(self):
        self.assertIsNone(get_active_entry(self.user))

    def test_get_active_entry_single(self):
        now = datetime.datetime.now()
        entry = factories.Entry(user=self.user, start_time=now)
        # not active
        factories.Entry(user=self.user, start_time=now,
                end_time=now)
        # different user
        factories.Entry(start_time=now)
        self.assertEqual(entry, get_active_entry(self.user))

    def test_get_active_entry_multiple(self):
        now = datetime.datetime.now()
        # two active entries for same user
        factories.Entry(user=self.user, start_time=now)
        factories.Entry(user=self.user, start_time=now)
        self.assertRaises(ActiveEntryError, get_active_entry, self.user)


class TestConstants(TestCase):

    def test_bad_format(self):
        with self.assertRaises(Exception):
            Constants(foo=('one',))
        with self.assertRaises(Exception):
            Constants(foo=('one', 'two', 'three'))

    def test_conflicting_codename(self):
        with self.assertRaises(Exception):
            Constants(choices=('2', 'two'))

    def test_choices(self):
        constants = Constants(foo=('1', 'one'), bar=('2', 'two'))
        choices = constants.choices()
        self.assertEquals(choices, [('1', 'one'), ('2', 'two')])

    def test_get_list(self):
        constants = Constants(foo=('1', 'one'), bar=('2', 'two'))
        clist = constants.get_list('foo', 'bar')
        self.assertEquals(clist, ['1', '2'])

    def test_get_list_bad_element(self):
        constants = Constants(foo=('1', 'one'), bar=('2', 'two'))
        with self.assertRaises(Exception):
            constants.get_list('foo', 'bar', 'baz')
