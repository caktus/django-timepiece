import datetime
import mock
from django.test import TestCase
from timepiece.templatetags import timepiece_tags as tags
from timepiece.tests.base import TimepieceDataTestCase


class HumanizeSecondsTestCase(TimepieceDataTestCase):

    def test_usual(self):
        seconds_display = tags.humanize_seconds((5.5 * 3600) + 3)
        self.assertEqual(seconds_display, u'05:30:03',
            "Should return u'05:30:03', returned {0}".format(seconds_display)
        )

    def test_negative_seconds(self):
        seconds_display = tags.humanize_seconds((-2.5 * 3600) - 4)
        self.assertEqual(seconds_display, u'(02:30:04)',
            "Should return u'(02:30:04)', returned {0}".format(seconds_display)
        )

    def test_overnight(self):
        seconds_display = tags.humanize_seconds((30 * 3600) + 2)
        self.assertEqual(seconds_display, u'30:00:02',
            "Should return u'30:00:02', returned {0}".format(seconds_display)
        )

    def test_format(self):
        seconds_display = tags.humanize_seconds(120, '%M:%M:%M')
        expected = u'02:02:02'
        self.assertEqual(seconds_display, expected,
            "Should return {0}, return {1}".format(expected, seconds_display)
        )


class ConvertHoursToSecondsTestCase(TimepieceDataTestCase):

    def test_usual(self):
        seconds = tags.convert_hours_to_seconds('3.25')
        expected = int(3.25 * 3600)
        self.assertEqual(seconds, expected,
            "Given 3.25 hours, returned {0}, expected {1}".format(
                seconds, expected)
        )

    def test_negative_seconds(self):
        seconds = tags.convert_hours_to_seconds('-2.75')
        expected = int(-2.75 * 3600)
        self.assertEqual(seconds, expected,
            "Given -2.75 hours, returned {0}, expected {1}".format(
                seconds, expected)
        )


class DateFiltersTagTestCase(TestCase):

    def test_default_options(self):
        # default everything we can
        # response looks like the right format roughly
        retval = tags.date_filters("FORM_ID")
        self.assertEqual("FORM_ID", retval['form_id'])
        filters = retval['filters']
        self.assertIn("Past 12 Months", filters)
        self.assertIn("Years", filters)
        self.assertIn("Quarters (Calendar Year)", filters)
        self.assertEqual(3, len(filters))
        self.assertEqual(2, len(retval))

    def test_months(self):
        # Look more closely at months response
        retval = tags.date_filters("FORM_ID", options=('months',))
        filter = retval['filters']['Past 12 Months']
        self.assertEqual(12, len(filter))
        for name, first_date, last_date in filter:
            # same month
            self.assertEqual(first_date[:3], last_date[:3])
            # same year
            self.assertEqual(first_date[-5:], last_date[-5:])
            # starts on the first
            self.assertEqual("/01/", first_date[2:6])

    def test_years(self):
        # Look more closely at years response
        retval = tags.date_filters("FORM_ID", options=('years',))
        filter = retval['filters']['Years']
        self.assertEqual(4, len(filter))
        for year, first_date, last_date in filter:
            # start on jan 1, 20xx
            self.assertTrue(first_date.startswith("01/01/20"))
            # end on Dec. 31, 20xx
            self.assertTrue(last_date.startswith("12/31/20"))
            # start and end in same year, "....../20xx"
            self.assertEqual(year, first_date[-4:])
            self.assertEqual(year, last_date[-4:])

    def test_quarters(self):
        # Look more closely at quarters response
        retval = tags.date_filters("FORM_ID", options=('quarters',))
        filter = retval['filters']['Quarters (Calendar Year)']
        self.assertEqual(8, len(filter))
        for name, first_date, last_date in filter:
            self.assertTrue(name.startswith("Q"))
            # starts on the first
            self.assertEqual("/01/", first_date[2:6])
            # start in the quarter we claim to
            self.assertEqual(name[-4:], first_date[-4:])
            # start and end in same year
            self.assertEqual(first_date[-4:], last_date[-4:])

    def test_no_use_range(self):
        # sniff test of turning off use_range
        retval = tags.date_filters("FORM_ID", options=('years',),
            use_range=False)
        filter = retval['filters']['Years']
        for year, first_date, last_date in filter:
            # first date is blank
            self.assertEqual('', first_date)


class TimeTagTestCase(TestCase):

    def test_seconds_to_hours(self):
        # basic math
        self.assertEqual(0.5, tags.seconds_to_hours(1800))
        self.assertEqual(2.0, tags.seconds_to_hours(7200))
        # rounding
        self.assertEqual(2.0, tags.seconds_to_hours(7201))

    def test_week_start(self):
        start = tags.week_start(datetime.date(2013, 1, 10))
        self.assertEqual("01/07/2013", start)

    def test_work_days(self):
        # Note: I'd prefer to use known dates and mock datetime so the
        # code thinks 'today' is whatever I want, but we can't mock
        # datetime because it's a native module. Boo.

        today = datetime.date.today()
        # Same day next week
        week_later = today + datetime.timedelta(days=7)
        num = tags.work_days(week_later)
        # from any day this week to the same day next week is 6 workdays,
        self.assertEqual(6, num)


class MiscTagTestCase(TestCase):

    def test_get_uninvoiced_hours(self):
        # uninvoiced hours are any hours without status 'invoiced' or
        # 'not-invoiced' [sic]
        class Entry(object):
            def __init__(self, status, hours):
                self.status = status
                self.hours = hours
        entries = [
            Entry('invoiced', 999),
            Entry('not-invoiced', 1),
            Entry('other', 37),
            Entry('shoes', 12)
        ]
        retval = tags.get_uninvoiced_hours(entries)
        self.assertEqual(49, retval)

    def test_timesheet_url(self):
        with mock.patch('timepiece.templatetags.timepiece_tags.reverse') \
          as reverse:
            reverse.return_value = "Boo"
            retval = tags.timesheet_url('project', 27, None)
            self.assertEqual('Boo?', retval)
            self.assertEqual('view_project_timesheet', reverse.call_args[0][0])
            self.assertEqual((27,), reverse.call_args[1]['args'])

    def test_timesheet_url2(self):
        with mock.patch('timepiece.templatetags.timepiece_tags.reverse')\
        as reverse:
            reverse.return_value = "Boo"
            dt = datetime.date(2013, 1, 10)
            retval = tags.timesheet_url('user', 13, dt)
            self.assertEqual('Boo?year=2013&month=1', retval)
            self.assertEqual('view_user_timesheet', reverse.call_args[0][0])
            self.assertEqual((13,), reverse.call_args[1]['args'])

    def test_project_report_url_for_contract(self):
        with mock.patch('timepiece.templatetags.timepiece_tags.reverse')\
        as reverse:
            reverse.return_value = "Boo"
            dt = datetime.date(2013, 1, 10)
            contract = mock.Mock(start_date=dt, end_date=dt)
            project = mock.Mock(id=54)
            retval = tags.project_report_url_for_contract(contract, project)
            url = 'Boo?billable=1&projects_1=54&from_date=' \
                '01%2F10%2F2013&to_date=01%2F10%2F2013&non_billable=1' \
                '&paid_leave=1&trunc=month'
            self.assertEqual(url, retval)
            self.assertEqual('report_hourly', reverse.call_args[0][0])


class SumHoursTagTestCase(TestCase):

    def setUp(self):
        class Entry(object):
            def __init__(self, seconds):
                self.seconds = seconds
            def get_total_seconds(self):
                return self.seconds

        self.entries = [
            Entry(1),
            Entry(2.5),
            Entry(5)
        ]

    def test_sum_hours(self):
        context = {}
        retval = tags.sum_hours(context, self.entries)
        self.assertEqual('', retval)
        self.assertEqual(8.5, context['daily_total'])

    def test_sum_hours_set_var_name(self):
        # again, different var name
        context = {}
        retval = tags.sum_hours(context, self.entries, 'foo_bar')
        self.assertEqual(8.5, context['foo_bar'])


class ArithmeticTagTestCase(TestCase):

    def test_multiply(self):
        self.assertEqual(1.0, tags.multiply(1, 1))
        self.assertEqual(1.5, tags.multiply(3, 0.5))
        # numbers can be strings
        self.assertEqual(3.0, tags.multiply("1.5", "2"))

    def test_get_max_hours(self):
        ctx = {
            'project_progress': [
                { 'worked': 1, 'assigned': 2},
                { 'worked': 3, 'assigned': 0},
                { 'worked': 2, 'assigned': 1},
            ]
        }
        self.assertEqual('3', tags.get_max_hours(ctx))

    def test_get_max_hours_min_is_zero(self):
        # min of max hours is zero
        ctx = {
            'project_progress': [
                { 'worked': -1, 'assigned': -4},
                { 'worked': -3, 'assigned': -5},
                ]
        }
        self.assertEqual('0', tags.get_max_hours(ctx))


class TestProjectHoursForContract(TimepieceDataTestCase):

    def setUp(self):
        self.user = self.create_user()

        self.a_project = self.create_project()
        self.another_project = self.create_project()
        self.billable_project = self.create_project(billable=True)
        self.project_without_hours = self.create_project()
        projects = [
            self.a_project,
            self.another_project,
            self.billable_project,
            self.project_without_hours
        ]

        self.contract = self.create_contract(projects=projects)

        start_time = datetime.datetime.now()
        one_hour = datetime.timedelta(hours=1)
        self.create_entry(data={
            'project': self.a_project,
            'start_time': start_time,
            'end_time': start_time + one_hour * 1
        })
        self.create_entry(data={
            'project': self.another_project,
            'start_time': start_time,
            'end_time': start_time + one_hour * 2
        })
        self.create_entry(data={
            'project': self.billable_project,
            'start_time': start_time,
            'end_time': start_time + one_hour * 4
        })

    def test_project_hours_for_contract(self):
        ctx = {}
        retval = tags.project_hours_for_contract(ctx, self.contract,
            self.a_project)
        self.assertEqual('', retval)
        self.assertEqual(1, ctx['project_hours'])

    def test_project_hours_for_contract_varname(self):
        # Specify a variable name, that's where the hours should go
        ctx = {}
        retval = tags.project_hours_for_contract(ctx, self.contract,
            self.another_project, variable='foo_bar')
        self.assertEqual('', retval)
        self.assertNotIn('project_hours', ctx)
        self.assertEqual(2, ctx['foo_bar'])

    def test_project_hours_for_contract_none(self):
        # Try it with the aggregate returning None
        ctx = {}
        retval = tags.project_hours_for_contract(ctx, self.contract,
            self.project_without_hours)
        self.assertEqual('', retval)
        self.assertEqual(0, ctx['project_hours'])
