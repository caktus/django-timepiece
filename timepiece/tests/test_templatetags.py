import datetime
from dateutil.relativedelta import relativedelta
import mock

from django import template
from django.test import TestCase
from django.utils.html import strip_tags

from timepiece import utils
from timepiece.templatetags import timepiece_tags as tags

from . import factories


class HumanizeTimeTestCase(TestCase):

    def test_seconds(self):
        seconds_display = tags.humanize_seconds((5.5 * 3600) + 3)
        expected = u'05:30:03'
        self.assertEquals(
            seconds_display, expected,
            "Should return {0}, returned {1}".format(expected, seconds_display)
        )

    def test_seconds_negative(self):
        seconds_display = tags.humanize_seconds((-2.5 * 3600) - 4)
        expected = u'-02:30:04'
        self.assertTrue(seconds_display.startswith('<span'))
        self.assertTrue('negative-time' in seconds_display)
        self.assertEquals(
            strip_tags(seconds_display), expected,
            "Should return {0}, returned {1}".format(expected, seconds_display)
        )

    def test_seconds_overnight(self):
        seconds_display = tags.humanize_seconds((30 * 3600) + 2)
        expected = u'30:00:02'
        self.assertEquals(
            seconds_display, expected,
            "Should return {0}, returned {1}".format(expected, seconds_display)
        )

    def test_seconds_format(self):
        seconds_display = tags.humanize_seconds(120, '{minutes:02d}:{minutes}')
        expected = u'02:2'
        self.assertEquals(
            seconds_display, expected,
            "Should return {0}, returned {1}".format(expected, seconds_display)
        )

    def test_seconds_negative_format(self):
        seconds_display = tags.humanize_seconds(-120, None, '-{minutes:02d}')
        expected = u'-02'
        self.assertEquals(
            seconds_display, expected,
            "Should return {0}, returned {1}".format(expected, seconds_display)
        )

    def test_hours(self):
        hours_display = tags.humanize_hours(7.5)
        expected = u'07:30:00'
        self.assertEquals(
            hours_display, expected,
            "Should return {0}, returned {1}".format(expected, hours_display)
        )

    def test_hours_format(self):
        hours_display = tags.humanize_hours(7.1, '{minutes:02d}:{minutes}')
        expected = u'06:6'
        self.assertEquals(
            hours_display, expected,
            "Should return {0}, returned {1}".format(expected, hours_display)
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
            # same month  "20xx-mm-dd"
            self.assertEqual(first_date[4:7], last_date[4:7])
            # same year
            self.assertEqual(first_date[:5], last_date[:5])
            # starts on the first
            self.assertEqual("-01", first_date[-3:])

    def test_years(self):
        # Look more closely at years response
        retval = tags.date_filters("FORM_ID", options=('years',))
        filter = retval['filters']['Years']
        self.assertEqual(4, len(filter))
        for year, first_date, last_date in filter:
            # start on jan 1, 20xx  "20xx-01-01"
            self.assertTrue(first_date.startswith("20") and first_date.endswith("-01-01"))
            # end on Dec. 31, 20xx  "20xx-12-31"
            self.assertTrue(last_date.startswith("20") and last_date.endswith("-12-31"))
            # start and end in same year, "20xx-"
            self.assertEqual(year, first_date[:4])
            self.assertEqual(year, last_date[:4])

    def test_quarters(self):
        # Look more closely at quarters response
        retval = tags.date_filters("FORM_ID", options=('quarters',))
        filter = retval['filters']['Quarters (Calendar Year)']
        self.assertEqual(8, len(filter))
        for name, first_date, last_date in filter:
            self.assertTrue(name.startswith("Q"))
            # starts on the first  "20xx-yy-01"
            self.assertEqual("-01", first_date[-3:])
            # start in the quarter we claim to
            self.assertEqual(name[-4:], first_date[:4])
            # start and end in same year
            self.assertEqual(first_date[:5], last_date[:5])

    def test_no_use_range(self):
        # sniff test of turning off use_range
        retval = tags.date_filters(
            "FORM_ID", options=('years',), use_range=False)
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
        self.assertEqual(start.date(), datetime.date(2013, 1, 7))


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
        self.assertEqual('{0:.2f}'.format(49.00), retval)

    def test_project_report_url_for_contract(self):
        dt = datetime.date(2013, 1, 10)
        contract = mock.Mock(start_date=dt, end_date=dt)
        project = mock.Mock(id=54)
        result = tags._project_report_url_params(contract, project)
        expected_url = {
            'from_date': '2013-01-10',
            'to_date': '2013-01-10',
            'billable': 1,
            'non_billable': 0,
            'paid_leave': 0,
            'trunc': 'month',
            'projects_1': project.id,
        }
        self.assertEqual(expected_url, result)


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
        retval = tags.sum_hours(self.entries)
        self.assertEqual(8.5, retval)


class ArithmeticTagTestCase(TestCase):

    def test_multiply(self):
        self.assertEqual(1.0, tags.multiply(1, 1))
        self.assertEqual(1.5, tags.multiply(3, 0.5))
        # numbers can be strings
        self.assertEqual(3.0, tags.multiply("1.5", "2"))

    def test_get_max_hours(self):
        ctx = {
            'project_progress': [
                {'worked': 1, 'assigned': 2},
                {'worked': 3, 'assigned': 0},
                {'worked': 2, 'assigned': 1},
            ]
        }
        self.assertEqual(3, tags.get_max_hours(ctx))

    def test_get_max_hours_min_is_zero(self):
        # min of max hours is zero
        ctx = {
            'project_progress': [
                {'worked': -1, 'assigned': -4},
                {'worked': -3, 'assigned': -5},
                ]
        }
        self.assertEqual(0, tags.get_max_hours(ctx))


class TestProjectHoursForContract(TestCase):

    def setUp(self):
        self.user = factories.User()

        self.a_project = factories.NonbillableProject()
        self.another_project = factories.NonbillableProject()
        self.billable_project = factories.BillableProject()
        self.project_without_hours = factories.NonbillableProject()
        projects = [
            self.a_project,
            self.another_project,
            self.billable_project,
            self.project_without_hours,
        ]

        self.contract = factories.ProjectContract(projects=projects)
        activity = factories.Activity(billable=True)
        unbillable_activity = factories.Activity(billable=False)

        start_time = datetime.datetime.now()
        factories.Entry(
            project=self.a_project, activity=activity, start_time=start_time,
            end_time=start_time + relativedelta(hours=1))
        factories.Entry(
            project=self.a_project, activity=unbillable_activity,
            start_time=start_time, end_time=start_time + relativedelta(hours=16))
        factories.Entry(
            project=self.another_project, activity=activity,
            start_time=start_time, end_time=start_time + relativedelta(hours=2))
        factories.Entry(
            project=self.billable_project, activity=activity,
            start_time=start_time, end_time=start_time + relativedelta(hours=4))
        factories.Entry(
            project=self.billable_project, activity=unbillable_activity,
            start_time=start_time, end_time=start_time + relativedelta(hours=8))

    def test_project_hours_for_contract(self):
        retval = tags.project_hours_for_contract(self.contract, self.a_project)
        # Includes billable and nonbillable by default
        self.assertEqual(17, retval)

    def test_project_hours_for_contract_none(self):
        # Try it with the aggregate returning None
        retval = tags.project_hours_for_contract(
            self.contract, self.project_without_hours)
        self.assertEqual(0, retval)

    def test_project_hours_for_contract_billable(self):
        # only include billable hours
        retval = tags.project_hours_for_contract(
            self.contract, self.billable_project, 'billable')
        self.assertEqual(4, retval)

    def test_project_hours_for_contract_nonbillable(self):
        # only include non-billable hours
        retval = tags.project_hours_for_contract(
            self.contract, self.billable_project, 'nonbillable')
        self.assertEqual(8, retval)

    def test_project_hours_for_contract_badbillable(self):
        # template tag does syntax check on the 'billable' arg
        with self.assertRaises(template.TemplateSyntaxError):
            tags.project_hours_for_contract(
                self.contract, self.a_project, 'invalidarg')


class AddParametersTest(TestCase):

    def test_new_parameters(self):
        """Tag should add parameters to base URL after a '?'."""
        url = '/hello/'
        params = {'foo': 'bar'}
        retval = tags.add_parameters(url, params)
        self.assertEqual(retval, url + '?foo=bar')

    def test_additional_parameters(self):
        """Tag should add parameters to base URL after a '&'."""
        url = '/hello/?user=1'
        params = {'foo': 'bar'}
        retval = tags.add_parameters(url, params)
        self.assertEqual(retval, url + '&foo=bar')

    def test_repeat_parameters(self):
        """Tag should append param even if another value exists for it."""
        url = '/hello/?foo=bar'
        params = {'foo': 'bar'}
        retval = tags.add_parameters(url, params)
        self.assertEqual(retval, url + '&foo=bar')

    def test_no_parameters(self):
        """Tag should return base URL when no parameters are given."""
        url = '/hello/'
        params = {}
        retval = tags.add_parameters(url, params)
        self.assertEqual(retval, url)

    def test_special_chars(self):
        """Tag should escape HTML entities."""
        url = '/hello/'
        params = {'foo': '?'}
        retval = tags.add_parameters(url, params)
        self.assertEqual(retval, url + '?foo=%3F')


class CreateDictTest(TestCase):

    def test_create_dict(self):
        retVal = tags.create_dict(foo='bar', a='b')
        self.assertEquals(len(retVal), 2)
        self.assertEquals(retVal['foo'], 'bar')
        self.assertEquals(retVal['a'], 'b')

    def test_create_empty_dict(self):
        retVal = tags.create_dict()
        self.assertEquals(retVal, {})


class AddTimezoneTest(TestCase):

    def test_add_timezone(self):
        d = datetime.datetime.now()
        retVal = tags.add_timezone(d)
        self.assertEquals(retVal, utils.add_timezone(d))
