import datetime
from dateutil.relativedelta import relativedelta
import json

from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse
from django.db.models import Q

from timepiece.forms import DATE_FORM_FORMAT
from timepiece.tests import factories
from timepiece.tests.base import ViewTestMixin, LogTimeMixin

from timepiece.entries.models import Entry
from timepiece.reports.tests.base import ReportsTestBase


class TestBillableHours(ViewTestMixin, LogTimeMixin, ReportsTestBase):

    def setUp(self):
        super(TestBillableHours, self).setUp()
        self.from_date = datetime.datetime(2011, 1, 2)
        self.to_date = datetime.datetime(2011, 1, 4)
        self.dates_data = ['12/27/2010', '01/03/2011']

        self.url = reverse('report_billable_hours')
        self.perm = Permission.objects.filter(codename='view_entry_summary')
        self.admin = factories.User()
        self.admin.user_permissions = self.perm

    def get_entries_data(self):
        # Account for the day added by the form
        query = Q(end_time__gte=self.from_date,
                  end_time__lt=self.to_date + relativedelta(days=1))
        return Entry.objects.date_trunc('week').filter(query)

    def test_access_permission(self):
        """view_entry_summary permission is required to view this report."""
        self.login_user(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_access_no_permission(self):
        """view_entry_summary permission is required to view this report."""
        self.login_user(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_response_data(self):
        """Test that the data returned is correct"""
        self.bulk_entries()
        self.login_user(self.admin)

        response = self.client.get(self.url, data={
            'from_date': self.from_date.strftime(DATE_FORM_FORMAT),
            'to_date': self.to_date.strftime(DATE_FORM_FORMAT),
            'trunc': 'week',
            'users': list(Entry.objects.values_list('user', flat=True)),
            'activities': list(Entry.objects.values_list('activity',
                                                         flat=True)),
            'project_types': list(Entry.objects.values_list('project__type',
                                                            flat=True)),
        })
        self.assertEqual(response.status_code, 200)

        entries_data = self.get_entries_data().order_by('user', 'date')  # noqa
        response_data = json.loads(response.context['data'])

        self.assertEqual(response_data[1][1:], [9, 9])
        self.assertEqual(response_data[2][1:], [18, 18])
