import datetime
from dateutil import relativedelta
import urllib
import re

from django.core.urlresolvers import reverse

from timepiece import models as timepiece
from timepiece.tests.base import TimepieceDataTestCase


class ProjectTestCase(TimepieceDataTestCase):

    def test_remove_user(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username=self.user.username, password='abc')
        self.assertEquals(self.project.users.all().count(), 1)
        url = reverse('remove_user_from_project',
            args=(self.project.pk, self.user.pk,))
        response = self.client.get(url, {'next': '/'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(self.project.users.all().count(), 0)

    def test_add_user(self):
        self.user.is_superuser = True
        self.user.save()

        self.client.login(username=self.user.username, password='abc')
        timepiece.ProjectRelationship.objects.all().delete()
        self.assertEquals(self.project.users.all().count(), 0)
        url = reverse('add_user_to_project', args=(self.project.pk,))
        response = self.client.post(url, {'user': self.user.pk, })
        self.assertEquals(response.status_code, 302)
        self.assertEquals(self.project.users.all().count(), 1)


class InvoiceTestCase(TimepieceDataTestCase):
    def setUp(self):
        super(InvoiceTestCase, self).setUp()
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username=self.user.username, password='abc')
        start = datetime.datetime(2011, 1, 1, 8, 0, 0)
        end = datetime.datetime(2011, 1, 1, 12, 0, 0)
        self.project_billable = self.create_project(billable=True)
        self.project_billable2 = self.create_project(billable=True)
        self.project_non_billable = self.create_project(billable=False)
        self.entry1 = self.create_entry({
            'user': self.user,
            'project': self.project_billable,
            'start_time': start,
            'end_time': end,
            'status': 'approved',
        })
        self.entry2 = self.create_entry({
            'user': self.user,
            'project': self.project_billable,
            'start_time': start - datetime.timedelta(days=5),
            'end_time': end - datetime.timedelta(days=5),
            'status': 'approved',
        })
        self.entry3 = self.create_entry({
            'user': self.user,
            'project': self.project_billable2,
            'start_time': start - datetime.timedelta(days=10),
            'end_time': end - datetime.timedelta(days=10),
            'status': 'approved',
        })
        self.entry4 = self.create_entry({
            'user': self.user,
            'project': self.project_non_billable,
            'start_time': start + datetime.timedelta(hours=11),
            'end_time': end + datetime.timedelta(hours=15),
            'status': 'approved',
        })

    def test_invoice_list(self):
        """
        Verify that only billable projects appear on the invoice list and that
        the links have accurate date information
        """
        url = reverse('invoice_projects')
        to_date = datetime.datetime(2011, 1, 31, 0, 0, 0)
        params = {'to_date': to_date.strftime('%m/%d/%Y')}
        response = self.client.get(url, params)
        # The number of projects should be 2 because entry4 has billable=False
        num_project_totals = len(response.context['project_totals'])
        self.assertEquals(num_project_totals, 2)
        # Verify that the date on the mark as invoiced links will be correct
        to_date_str = response.context['to_date'].strftime('%Y %m %d')
        self.assertEquals(to_date_str, '2011 01 31')

    def test_invoice_list_requires_to(self):
        """Verify that only the invoice list is blank without a to date"""
        url = reverse('invoice_projects')
        params = {'to_date': ''}
        response = self.client.get(url, params)
        # The number of projects should be 1 because entry3 has billable=False
        num_project_totals = len(response.context['project_totals'])
        self.assertEquals(num_project_totals, 0)

    def test_invoice_list_with_from(self):
        # Add another entry and make sure from filters it out
        url = reverse('invoice_projects')
        from_date = datetime.datetime(2011, 1, 1, 0, 0, 0)
        to_date = datetime.datetime(2011, 1, 31, 0, 0, 0)
        params = {
            'from_date': from_date.strftime('%m/%d/%Y'),
            'to_date': to_date.strftime('%m/%d/%Y'),
        }
        response = self.client.get(url, params)
        # From date filters out one entry
        num_project_totals = len(response.context['project_totals'])
        self.assertEquals(num_project_totals, 1)
        # Verify that the date on the mark as invoiced links will be correct
        from_date_str = response.context['from_date'].strftime('%Y %m %d')
        self.assertEquals(from_date_str, '2011 01 01')
        to_date_str = response.context['to_date'].strftime('%Y %m %d')
        self.assertEquals(to_date_str, '2011 01 31')

    def test_invoice_view(self):
        to_date = datetime.datetime(2011, 1, 31)
        args = [self.project_billable.id, to_date.strftime('%Y-%m-%d')]
        url = reverse('time_sheet_invoice_project', args=args)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        to_date_str = response.context['to_date'].strftime('%Y %m %d')
        self.assertEqual(to_date_str, '2011 01 31')
        # View can also take from date
        from_date = datetime.datetime(2011, 1, 1)
        args = [
            self.project_billable.id,
            to_date.strftime('%Y-%m-%d'),
            from_date.strftime('%Y-%m-%d')
        ]
        url = reverse('time_sheet_invoice_project', args=args)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        from_date_str = response.context['from_date'].strftime('%Y %m %d')
        to_date_str = response.context['to_date'].strftime('%Y %m %d')
        self.assertEqual(from_date_str, '2011 01 01')
        self.assertEqual(to_date_str, '2011 01 31')

    def test_invoice_bad_args(self):
        # A year/month/project with no entries should raise a 404
        args = [self.project_billable.id, '2008-01-13']
        url = reverse('time_sheet_invoice_project', args=args)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        # A year/month with bad/overflow values should raise a 404
        args = [self.project_billable.id, '9999-13-01']
        url = reverse('time_sheet_invoice_project', args=args)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_make_invoice(self):
        to_date = datetime.datetime(2011, 1, 31)
        args = [self.project_billable.id, to_date.strftime('%Y-%m-%d')]
        url = reverse('time_sheet_invoice_project', args=args)
        response = self.client.post(url, {'number': 3, 'status': 'invoiced'})
        self.assertEqual(response.status_code, 302)
        # Verify an invoice was created with the correct attributes
        invoice = timepiece.EntryGroup.objects.get(number=3)
        self.assertEqual(invoice.project.id, self.project_billable.id)
        self.assertEqual(invoice.start, None)
        self.assertEqual(invoice.end.strftime('%Y %m %d'), '2011 01 31')
        self.assertEqual(len(invoice.entries.all()), 2)
        # Verify that the entries were invoiced appropriately
        # and the unrelated entries were untouched
        entries = timepiece.Entry.objects.all()
        invoiced = entries.filter(status='invoiced')
        for entry in invoiced:
            self.assertEqual(entry.entry_group_id, invoice.id)
        approved = entries.filter(status='approved')
        self.assertEqual(len(approved), 2)
        self.assertEqual(approved[0].entry_group_id, None)

    def test_make_invoice_with_from_uninvoiced(self):
        from_date = datetime.datetime(2011, 1, 1)
        to_date = datetime.datetime(2011, 1, 31)
        from_date = datetime.datetime(2011, 1, 1)
        args = [
            self.project_billable.id,
            to_date.strftime('%Y-%m-%d'),
            from_date.strftime('%Y-%m-%d')
        ]
        url = reverse('time_sheet_invoice_project', args=args)
        response = self.client.post(url, {'number': 5,
                                          'status': 'not-invoiced'})
        self.assertEqual(response.status_code, 302)
        # Verify an invoice was created with the correct attributes
        invoice = timepiece.EntryGroup.objects.get(number=5)
        self.assertEqual(invoice.project.id, self.project_billable.id)
        self.assertEqual(invoice.start.strftime('%Y %m %d'), '2011 01 01')
        self.assertEqual(invoice.end.strftime('%Y %m %d'), '2011 01 31')
        self.assertEqual(len(invoice.entries.all()), 1)
        # Verify that the entries were invoiced appropriately
        # and the unrelated entries were untouched
        entries = timepiece.Entry.objects.all()
        uninvoiced = entries.filter(status='uninvoiced')
        for entry in uninvoiced:
            self.assertEqual(entry.entry_group_id, invoice.id)

    def test_invoice_bad_number(self):
        to_date = datetime.datetime(2011, 1, 31)
        args = [self.project_billable.id, to_date.strftime('%Y-%m-%d')]
        url = reverse('time_sheet_invoice_project', args=args)
        response = self.client.post(url, {'number': 'string'})
        err_msg = 'Enter a whole number.'
        self.assertFormError(response, 'invoice_form', 'number', err_msg)
        response = self.client.post(url, {'number': None})
        self.assertFormError(response, 'invoice_form', 'number', err_msg)
