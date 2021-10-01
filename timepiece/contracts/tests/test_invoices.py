import datetime
from dateutil.relativedelta import relativedelta
import random

from six.moves.urllib.parse import urlencode

from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse
from django.test import TestCase

from timepiece import utils
from timepiece.forms import DATE_FORM_FORMAT
from timepiece.tests import factories
from timepiece.tests.base import ViewTestMixin, LogTimeMixin

from timepiece.contracts.models import EntryGroup, HourGroup
from timepiece.crm.models import Attribute
from timepiece.entries.models import Activity, Entry


class TestListInvoicesView(ViewTestMixin, TestCase):
    url_name = 'list_invoices'
    template_name = 'timepiece/invoice/list.html'
    factory = factories.EntryGroup
    model = EntryGroup

    def setUp(self):
        super(TestListInvoicesView, self).setUp()
        self.permissions = [Permission.objects.get(codename='add_entrygroup')]
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)

    def test_list_all(self):
        """If no filters are provided, all objects should be listed."""
        object_list = [self.factory.create() for i in range(3)]
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 3)
        for obj in object_list:
            self.assertTrue(obj in response.context['object_list'])

    def test_list_one(self):
        """Page should render if there is one object & no search query."""
        obj = self.factory.create()
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 1)
        self.assertEquals(response.context['object_list'].get(), obj)

    def test_no_results(self):
        """Page should render if there are no search results."""
        self.factory.create()
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 0)

    def test_one_result(self):
        """Page should render if there is only one search result."""
        obj = self.factory.create(comments='hello')
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 1)
        self.assertEquals(response.context['object_list'].get(), obj)

    def test_multiple_results(self):
        """Page should render if there are multiple search results."""
        obj_list = [self.factory.create(comments='hello') for i in range(2)]
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 2)
        for obj in obj_list:
            self.assertTrue(obj in response.context['object_list'])

    def test_filter_number(self):
        """User should be able to filter by search query."""
        obj = self.factory.create(number='hello')
        self.factory.create()
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object_list'].get(), obj)

    def test_filter_comments(self):
        """User should be able to filter by search query."""
        obj = self.factory.create(comments='hello')
        self.factory.create()
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object_list'].get(), obj)

    def test_filter_project_name(self):
        """User should be able to filter by search query."""
        obj = self.factory.create(project__name='hello')
        self.factory.create()
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object_list'].get(), obj)

    def test_filter_user_username(self):
        """User should be able to filter by search query."""
        obj = self.factory.create(user__username='hello')
        self.factory.create()
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object_list'].get(), obj)


class InvoiceViewPreviousTestCase(ViewTestMixin, LogTimeMixin, TestCase):

    def setUp(self):
        super(InvoiceViewPreviousTestCase, self).setUp()
        self.user = factories.Superuser()
        self.login_user(self.user)
        self.devl_activity = factories.Activity(
            code='devl', name='development', billable=True)
        self.activity = factories.Activity(
            code='WRK', name='Work')
        # Make some projects and entries for invoice creation
        self.project = factories.BillableProject()
        self.project2 = factories.BillableProject()
        last_start = self.log_many([self.project, self.project2])
        # Add some non-billable entries
        self.log_many([self.project, self.project2], start=last_start,
                      billable=False)
        self.create_invoice(self.project, {'static': EntryGroup.INVOICED})
        self.create_invoice(self.project2, {'status': EntryGroup.NOT_INVOICED})

    def get_create_url(self, **kwargs):
        base_url = reverse('create_invoice')
        params = urlencode(kwargs)
        return '{0}?{1}'.format(base_url, params)

    def log_many(self, projects, num_entries=20, start=None, billable=True):
        start = utils.add_timezone(datetime.datetime(2011, 1, 1, 0, 0, 0))
        for index in range(0, num_entries):
            start += relativedelta(hours=(5 * index))
            project = projects[index % len(projects)]  # Alternate projects
            self.log_time(start=start, status=Entry.APPROVED, project=project,
                          billable=billable)
        return start

    def create_invoice(self, project=None, data=None):
        data = data or {}
        if not project:
            project = self.project
        to_date = utils.add_timezone(datetime.datetime(2011, 1, 31))
        url = self.get_create_url(project=project.id, to_date=to_date.strftime('%Y-%m-%d'))
        params = {
            'number': str(random.randint(999, 9999)),
            'status': EntryGroup.INVOICED,
        }
        params.update(data)
        self.client.post(url, params)

    def get_invoice(self):
        invoices = EntryGroup.objects.all()
        return random.choice(invoices)

    def get_entry(self, invoice):
        entries = invoice.entries.all()
        return random.choice(entries)

    def test_previous_invoice_list_no_search(self):
        url = reverse('list_invoices')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        invoices = response.context['object_list']
        self.assertEqual(len(invoices), 2)

    def test_previous_invoice_list_search(self):

        def search(query):
            response = self.client.get(list_url, data={'search': query})
            return response.context['object_list']

        list_url = reverse('list_invoices')
        project3 = factories.BillableProject(name=':-D')
        self.log_many([project3], 10)
        self.create_invoice(project=project3, data={
            'status': EntryGroup.INVOICED,
            'comments': 'comment!',
            'number': '###',
        })

        # Search comments, project name, and number.
        for query in ['comment!', ':-D', '###']:
            results = search(query)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].project, project3)

        # Search in username
        results = search(self.user.username)
        self.assertEqual(len(results), 3)  # all were created by this user

        # No results
        results = search("You won't find me here")
        self.assertEquals(len(results), 0)

    def test_invoice_detail(self):
        invoices = EntryGroup.objects.all()
        for invoice in invoices:
            url = reverse('view_invoice', args=[invoice.id])
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['invoice'])

    def test_invoice_csv(self):
        invoice = self.get_invoice()
        url = reverse('view_invoice_csv', args=[invoice.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = dict(response.items())
        self.assertEqual(data['Content-Type'], 'text/csv')
        disposition = data['Content-Disposition']
        self.assertTrue(disposition.startswith('attachment; filename=Invoice'))
        contents = response.content.decode('utf-8').splitlines()
        # TODO: Possibly find a meaningful way to test contents
        # Pull off header line and totals line
        contents.pop(0)  # header
        contents.pop()  # totals
        num_entries = invoice.entries.all().count()
        self.assertEqual(num_entries, len(contents))

    def test_invoice_csv_bad_id(self):
        url = reverse('view_invoice_csv', args=[9999999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_invoice_edit_get(self):
        invoice = self.get_invoice()
        url = reverse('edit_invoice', args=[invoice.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['invoice'].id, invoice.id)
        self.assertTrue(response.context['entries'])

    def test_invoice_edit_bad_id(self):
        url = reverse('edit_invoice', args=[99999999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_invoice_edit_post(self):
        invoice = self.get_invoice()
        url = reverse('edit_invoice', args=(invoice.id,))
        if invoice.status != EntryGroup.INVOICED:
            status = EntryGroup.INVOICED
        else:
            status = EntryGroup.NOT_INVOICED
        params = {
            'number': int(invoice.number) + 1,
            'status': status,
            'comments': 'Comments',
        }
        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 302)
        new_invoice = EntryGroup.objects.get(pk=invoice.id)
        self.assertEqual(int(invoice.number) + 1, int(new_invoice.number))
        self.assertTrue(invoice.status != new_invoice.status)
        self.assertEqual(new_invoice.comments, 'Comments')

    def test_invoice_edit_bad_post(self):
        invoice = self.get_invoice()
        url = reverse('edit_invoice', args=[invoice.id])
        params = {
            'number': '2',
            'status': 'not_in_choices',
        }
        response = self.client.post(url, params)
        err_msg = 'Select a valid choice. not_in_choices is not one of ' + \
                  'the available choices.'
        self.assertFormError(response, 'invoice_form', 'status', err_msg)

    def test_invoice_delete_get(self):
        invoice = self.get_invoice()
        url = reverse('delete_invoice', args=[invoice.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_invoice_delete(self):
        invoice = self.get_invoice()
        entry_ids = [entry.pk for entry in invoice.entries.all()]
        url = reverse('delete_invoice', args=[invoice.id])
        response = self.client.post(url, {'delete': 'delete'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(EntryGroup.objects.filter(pk=invoice.id))
        entries = Entry.objects.filter(pk__in=entry_ids)
        for entry in entries:
            self.assertEqual(entry.status, Entry.APPROVED)

    def test_invoice_delete_cancel(self):
        invoice = self.get_invoice()
        url = reverse('delete_invoice', args=[invoice.id])
        response = self.client.post(url, {'cancel': 'cancel'})
        self.assertEqual(response.status_code, 302)
        # Canceled out so the invoice was not deleted
        self.assertTrue(EntryGroup.objects.get(pk=invoice.id))

    def test_invoice_delete_bad_args(self):
        self.get_invoice()
        url = reverse('delete_invoice', args=[1232345345])
        response = self.client.post(url, {'delete': 'delete'})
        self.assertEqual(response.status_code, 404)

    def test_rm_invoice_entry_get(self):
        invoice = self.get_invoice()
        entry = self.get_entry(invoice)
        url = reverse('delete_invoice_entry', args=[invoice.id, entry.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['invoice'], invoice)
        self.assertEqual(response.context['entry'], entry)

    def test_rm_invoice_entry_get_bad_id(self):
        invoice = self.get_invoice()
        entry = self.get_entry(invoice)
        url = reverse('delete_invoice_entry', args=[invoice.id, 999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        url = reverse('delete_invoice_entry', args=[9999, entry.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_rm_invoice_entry_post(self):
        invoice = self.get_invoice()
        entry = self.get_entry(invoice)
        url = reverse('delete_invoice_entry', args=[invoice.id, entry.id])
        response = self.client.post(url, {'submit': ''})
        self.assertEqual(response.status_code, 302)
        new_invoice = EntryGroup.objects.get(pk=invoice.pk)
        rm_entry = new_invoice.entries.filter(pk=entry.id)
        self.assertFalse(rm_entry)
        new_entry = Entry.objects.get(pk=entry.pk)
        self.assertEqual(new_entry.status, Entry.APPROVED)
        self.assertEqual(new_entry.entry_group, None)


class InvoiceCreateTestCase(ViewTestMixin, TestCase):

    def setUp(self):
        super(InvoiceCreateTestCase, self).setUp()
        self.user = factories.Superuser()
        self.login_user(self.user)
        start = utils.add_timezone(datetime.datetime(2011, 1, 1, 8))
        end = utils.add_timezone(datetime.datetime(2011, 1, 1, 12))
        self.project_billable = factories.BillableProject()
        self.project_billable2 = factories.BillableProject()
        self.project_non_billable = factories.NonbillableProject()
        self.entry1 = factories.Entry(
            user=self.user, project=self.project_billable,
            activity=factories.Activity(billable=True),
            start_time=start, end_time=end, status=Entry.APPROVED)
        self.entry2 = factories.Entry(
            user=self.user, project=self.project_billable,
            activity=factories.Activity(billable=True),
            start_time=start - relativedelta(days=5),
            end_time=end - relativedelta(days=5), status=Entry.APPROVED)
        self.entry3 = factories.Entry(
            user=self.user, project=self.project_billable2,
            activity=factories.Activity(billable=False),
            start_time=start - relativedelta(days=10),
            end_time=end - relativedelta(days=10), status=Entry.APPROVED)
        self.entry4 = factories.Entry(
            user=self.user, project=self.project_non_billable,
            start_time=start + relativedelta(hours=11),
            end_time=end + relativedelta(hours=15), status=Entry.APPROVED)

    def get_create_url(self, **kwargs):
        base_url = reverse('create_invoice')
        params = urlencode(kwargs)
        return '{0}?{1}'.format(base_url, params)

    def make_hourgroups(self):
        """
        Make several hour groups, one for each activity, and one that contains
        all activities to check for hour groups with multiple activities.
        """
        all_activities = Activity.objects.all()
        for activity in all_activities:
            hg = HourGroup.objects.create(name=activity.name)
            hg.activities.add(activity)

    def login_with_permission(self):
        """Helper to login as user with correct permissions"""
        generate_invoice = Permission.objects.get(
            codename='generate_project_invoice')
        user = factories.User()
        user.user_permissions.add(generate_invoice)

    def test_invoice_confirm_view_user(self):
        """A regular user should not be able to access this page"""
        self.login_user(factories.User())
        to_date = utils.add_timezone(datetime.datetime(2011, 1, 31))
        url = self.get_create_url(
            project=self.project_billable.pk,
            to_date=to_date.strftime(DATE_FORM_FORMAT))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 403)

    def test_invoice_confirm_view_permission(self):
        """
        If you have the correct permission, you should be
        able to create an invoice
        """
        self.login_with_permission()
        to_date = utils.add_timezone(datetime.datetime(2011, 1, 31))
        url = self.get_create_url(
            project=self.project_billable.pk,
            to_date=to_date.strftime(DATE_FORM_FORMAT))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_invoice_confirm_view(self):
        to_date = utils.add_timezone(datetime.datetime(2011, 1, 31))
        url = self.get_create_url(
            project=self.project_billable.pk,
            to_date=to_date.strftime(DATE_FORM_FORMAT))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        to_date_str = response.context['to_date'].strftime('%Y %m %d')
        self.assertEqual(to_date_str, '2011 01 31')
        # View can also take from date
        from_date = utils.add_timezone(datetime.datetime(2011, 1, 1))
        kwargs = {
            'project': self.project_billable.id,
            'to_date': to_date.strftime(DATE_FORM_FORMAT),
            'from_date': from_date.strftime(DATE_FORM_FORMAT),
        }
        url = self.get_create_url(**kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        from_date_str = response.context['from_date'].strftime('%Y %m %d')
        to_date_str = response.context['to_date'].strftime('%Y %m %d')
        self.assertEqual(from_date_str, '2011 01 01')
        self.assertEqual(to_date_str, '2011 01 31')

    def test_invoice_confirm_totals(self):
        """Verify that the per activity totals are valid."""
        ACTIVITY_NAME = 'activity_n'
        # Make a few extra entries to test per activity totals
        start = utils.add_timezone(datetime.datetime(2011, 1, 1, 8))
        end = utils.add_timezone(datetime.datetime(2011, 1, 1, 12))
        # start = utils.add_timezone(datetime.datetime.now())
        # end = start + relativedelta(hours=4)
        activity = factories.Activity(billable=True, name=ACTIVITY_NAME)
        for num in range(0, 4):
            factories.Entry(
                user=self.user, project=self.project_billable,
                start_time=start - relativedelta(days=num),
                end_time=end - relativedelta(days=num),
                status=Entry.APPROVED, activity=activity)
        self.make_hourgroups()
        to_date = datetime.datetime(2011, 1, 31)
        kwargs = {
            'project': self.project_billable.id,
            'to_date': to_date.strftime(DATE_FORM_FORMAT),
        }
        url = self.get_create_url(**kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        for name, hours_activities in response.context['billable_totals']:
            total, activities = hours_activities
            if name == ACTIVITY_NAME:
                self.assertEqual(total, 16)
                self.assertEqual(total, activities[0][1])
                self.assertEqual(name, activities[0][0])
            elif name == 'Total':
                self.assertEqual(total, 24)
                self.assertEqual(activities, [])
            else:
                # Each other activity is 4 hrs each
                self.assertEqual(total, 4)
                self.assertEqual(total, activities[0][1])
                self.assertEqual(name, activities[0][0])

    def test_invoice_confirm_rounding(self):
        """Verify that the per activity totals are rounded correctly."""
        ACTIVITY_NAME = 'activity_n'
        # Make a few extra entries to test per activity totals
        start = utils.add_timezone(datetime.datetime(2011, 1, 1, 8, 0, 0))
        end = utils.add_timezone(datetime.datetime(2011, 1, 1, 8, 3, 1))
        # 3m1s = 0.05166667h
        # 0.05166667 rounds to 0.05, at two decimal places
        # 0.05 * 5 = 0.25
        # 0.05166667 * 5 = 0.25833335
        # 0.25833335 rounds to 0.26, at two decimal places
        # If rounding happens before summation, then the total will be 0.25
        # If rounding happens after summation, then the total will be 0.26

        activity = factories.Activity(billable=True, name=ACTIVITY_NAME)
        for num in range(0, 5):
            factories.Entry(
                user=self.user, project=self.project_billable,
                start_time=start - relativedelta(days=num),
                end_time=end - relativedelta(days=num),
                status=Entry.APPROVED, activity=activity)
        self.make_hourgroups()
        to_date = datetime.datetime(2011, 1, 31)
        kwargs = {
            'project': self.project_billable.id,
            'to_date': to_date.strftime(DATE_FORM_FORMAT),
        }
        url = self.get_create_url(**kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        for name, hours_activities in response.context['billable_totals']:
            total, activities = hours_activities
            if name == ACTIVITY_NAME:
                self.assertEqual(total, 0.25)
                self.assertNotAlmostEqual(float(total), 0.26, places=2)

    def test_invoice_confirm_bad_args(self):
        # A year/month/project with no entries should raise a 404
        kwargs = {
            'project': self.project_billable.id,
            'to_date': '2008-01-13',
        }
        url = self.get_create_url(**kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        # A year/month with bad/overflow values should raise a 404
        kwargs = {
            'project': self.project_billable.id,
            'to_date': '9999-13-01',
        }
        url = self.get_create_url(**kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_make_invoice(self):
        to_date = utils.add_timezone(datetime.datetime(2011, 1, 31))
        kwargs = {
            'project': self.project_billable.id,
            'to_date': to_date.strftime(DATE_FORM_FORMAT),
        }
        url = self.get_create_url(**kwargs)
        response = self.client.post(url, {
            'number': '3',
            'status': EntryGroup.INVOICED,
        })
        self.assertEqual(response.status_code, 302)
        # Verify an invoice was created with the correct attributes
        invoice = EntryGroup.objects.get(number=3)
        self.assertEqual(invoice.project.id, self.project_billable.id)
        self.assertEqual(invoice.start, None)
        self.assertEqual(invoice.end.strftime('%Y %m %d'), '2011 01 31')
        self.assertEqual(len(invoice.entries.all()), 2)
        # Verify that the entries were invoiced appropriately
        # and the unrelated entries were untouched
        entries = Entry.objects.all()
        invoiced = entries.filter(status=EntryGroup.INVOICED)
        for entry in invoiced:
            self.assertEqual(entry.entry_group_id, invoice.id)
        approved = entries.filter(status=Entry.APPROVED)
        self.assertEqual(len(approved), 2)
        self.assertEqual(approved[0].entry_group_id, None)

    def test_make_invoice_with_from_uninvoiced(self):
        from_date = utils.add_timezone(datetime.datetime(2011, 1, 1))
        to_date = utils.add_timezone(datetime.datetime(2011, 1, 31))
        kwargs = {
            'project': self.project_billable.id,
            'to_date': to_date.strftime(DATE_FORM_FORMAT),
            'from_date': from_date.strftime(DATE_FORM_FORMAT),
        }
        url = self.get_create_url(**kwargs)
        response = self.client.post(url, {'number': '5',
                                          'status': EntryGroup.NOT_INVOICED})
        self.assertEqual(response.status_code, 302)
        # Verify an invoice was created with the correct attributes
        invoice = EntryGroup.objects.get(number=5)
        self.assertEqual(invoice.project.id, self.project_billable.id)
        self.assertEqual(invoice.start.strftime('%Y %m %d'), '2011 01 01')
        self.assertEqual(invoice.end.strftime('%Y %m %d'), '2011 01 31')
        self.assertEqual(len(invoice.entries.all()), 1)
        # Verify that the entries were invoiced appropriately
        # and the unrelated entries were untouched
        entries = Entry.objects.all()
        uninvoiced = entries.filter(status=Entry.NOT_INVOICED)
        for entry in uninvoiced:
            self.assertEqual(entry.entry_group_id, invoice.id)


class ListOutstandingInvoicesViewTestCase(ViewTestMixin, TestCase):
    url_name = 'list_outstanding_invoices'

    def setUp(self):
        super(ListOutstandingInvoicesViewTestCase, self).setUp()
        self.user = factories.Superuser()
        self.login_user(self.user)

        start = utils.add_timezone(datetime.datetime(2011, 1, 1, 8))
        end = utils.add_timezone(datetime.datetime(2011, 1, 1, 12))

        self.project_billable = factories.BillableProject()
        self.project_billable2 = factories.BillableProject()
        self.project_non_billable = factories.NonbillableProject()

        self.entry1 = factories.Entry(
            user=self.user, project=self.project_billable,
            activity=factories.Activity(billable=True),
            start_time=start, end_time=end, status=Entry.APPROVED)
        self.entry2 = factories.Entry(
            user=self.user, project=self.project_billable,
            activity=factories.Activity(billable=True),
            start_time=start - relativedelta(days=5),
            end_time=end - relativedelta(days=5), status=Entry.APPROVED)
        self.entry3 = factories.Entry(
            user=self.user, project=self.project_billable2,
            activity=factories.Activity(billable=False),
            start_time=start - relativedelta(days=10),
            end_time=end - relativedelta(days=10), status=Entry.APPROVED)
        self.entry4 = factories.Entry(
            user=self.user, project=self.project_non_billable,
            start_time=start + relativedelta(hours=11),
            end_time=end + relativedelta(hours=15), status=Entry.APPROVED)

        # Default get kwargs.
        self.to_date = utils.add_timezone(datetime.datetime(2011, 1, 31, 0, 0, 0))
        self.get_kwargs = {
            'to_date': self.to_date.strftime(DATE_FORM_FORMAT),
            'statuses': list(Attribute.statuses.values_list('pk', flat=True)),
        }

    def test_unauthenticated(self):
        self.client.logout()
        response = self._get()
        self.assertEquals(response.status_code, 302)

    def test_list_no_kwargs(self):
        response = self._get(get_kwargs={})
        self.assertEquals(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_bound)
        self.assertFalse(form.is_valid())
        self.assertEquals(response.context['project_totals'].count(), 3)

    def test_list_outstanding(self):
        """Only billable projects should be listed."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        form = response.context['form']
        self.assertTrue(form.is_valid(), form.errors)
        # The number of projects should be 3 because entry4 has billable=False
        self.assertEquals(response.context['project_totals'].count(), 3)
        # Verify that the date on the mark as invoiced links will be correct
        self.assertEquals(response.context['to_date'], self.to_date.date())
        self.assertEquals(list(response.context['unverified']), [])
        self.assertEquals(list(response.context['unapproved']), [])

    def test_unverified(self):
        start = utils.add_timezone(datetime.datetime(2011, 1, 1, 8))
        end = utils.add_timezone(datetime.datetime(2011, 1, 1, 12))
        factories.Entry(
            user=self.user,
            project=self.project_non_billable,
            start_time=start + relativedelta(hours=11),
            end_time=end + relativedelta(hours=15), status=Entry.UNVERIFIED
        )  # unverified
        response = self._get()
        self.assertEquals(response.status_code, 200)
        form = response.context['form']
        self.assertTrue(form.is_valid(), form.errors)
        unverified = list(response.context['unverified'])
        unapproved = list(response.context['unapproved'])
        expected_unverified = [
            (self.user.pk, self.user.first_name, self.user.last_name)
        ]
        self.assertEquals(unverified, expected_unverified)
        self.assertEquals(unapproved, [])

    def test_approved(self):
        start = utils.add_timezone(datetime.datetime(2011, 1, 1, 8))
        end = utils.add_timezone(datetime.datetime(2011, 1, 1, 12))
        unapproved_entry_a = factories.Entry(
            user=self.user, project=self.project_non_billable,
            start_time=start + relativedelta(hours=11),
            end_time=end + relativedelta(hours=15), status=Entry.VERIFIED)
        unapproved_entry_b = factories.Entry(
            user=self.user, project=self.project_non_billable,
            start_time=start + relativedelta(hours=11),
            end_time=end + relativedelta(hours=15), status=Entry.VERIFIED)
        response = self._get()
        self.assertEquals(response.status_code, 200)
        form = response.context['form']
        self.assertTrue(form.is_valid(), form.errors)
        unverified = set(response.context['unverified'])
        unapproved = set(response.context['unapproved'])
        user_a, user_b = unapproved_entry_a.user, unapproved_entry_b.user
        expected_unapproved = set([
            (user_a.pk, user_a.first_name, user_a.last_name),
            (user_b.pk, user_b.first_name, user_b.last_name),
        ])
        self.assertEquals(unverified, set())
        self.assertEquals(unapproved, expected_unapproved)

    def test_no_statuses(self):
        self.get_kwargs.pop('statuses')
        response = self._get()
        self.assertEquals(response.status_code, 200)
        form = response.context['form']
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEquals(response.context['project_totals'].count(), 0)

    def test_to_date_required(self):
        """to_date is required."""
        self.get_kwargs['to_date'] = ''
        response = self._get()
        self.assertEquals(response.status_code, 200)
        form = response.context['form']
        self.assertFalse(form.is_valid(), form.errors)
        # The number of projects should be 1 because entry3 has billable=False
        self.assertEquals(response.context['project_totals'].count(), 0)

    def test_from_date(self):
        from_date = utils.add_timezone(datetime.datetime(2011, 1, 1, 0, 0, 0))
        self.get_kwargs['from_date'] = from_date.strftime(DATE_FORM_FORMAT)
        response = self._get()
        self.assertEquals(response.status_code, 200)
        form = response.context['form']
        self.assertTrue(form.is_valid(), form.errors)
        # From date filters out one entry
        self.assertEquals(response.context['project_totals'].count(), 1)
        # Verify that the date on the mark as invoiced links will be correct
        self.assertEquals(response.context['to_date'], self.to_date.date())
        self.assertEquals(response.context['from_date'], from_date.date())
