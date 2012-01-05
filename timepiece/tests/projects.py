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
            'start_time': start,
            'end_time': end,
            'status': 'approved',
        })
        self.entry3 = self.create_entry({
            'user': self.user,
            'project': self.project_non_billable,
            'start_time': self.entry1.start_time + datetime.timedelta(hours=11),
            'end_time': self.entry1.end_time + datetime.timedelta(hours=15),
            'status': 'approved',
        })

    def test_invoice_list(self):
        """
        Verify that only billable projects appear on the invoice list and that
        the links have accurate date information
        """
        url = reverse('invoice_projects')
        params = {
            'year': 2011,
            'month': 1,
        }
        response = self.client.get(url, params)
        # The number of projects should be 1 because entry3 has billable=False
        num_project_totals = len(response.context['project_totals'])
        self.assertEquals(num_project_totals, 1)
        # Verify that the date on the mark as invoiced links are correct
        correct_begin = self.entry1.start_time + \
            relativedelta.relativedelta(day=1)
        correct_end = self.entry1.end_time + \
            relativedelta.relativedelta(months=+1, day=1)
        from_date_str = response.context['from_date'].strftime('%Y %m %d')
        to_date_str = response.context['to_date'].strftime('%Y %m %d')
        self.assertEquals(from_date_str, '2011 01 01')
        self.assertEquals(to_date_str, '2011 01 31')

    def test_make_invoice(self):
        args = [self.project_billable.id, 2011, 1]
        url = reverse('time_sheet_invoice_project', args=args)
        response = self.client.post(url, {'number': 3})
        self.assertEqual(response.status_code, 302)
        # Verify an invoice was created with the correct attributes
        invoice = timepiece.Invoice.objects.get(number=3)
        self.assertEqual(invoice.project.id, self.project_billable.id)
        self.assertEqual(invoice.start.strftime('%Y %m %d'), '2011 01 01')
        self.assertEqual(invoice.end.strftime('%Y %m %d'), '2011 02 01')
        self.assertEqual(len(invoice.entries.all()), 2)
        # Verify that the entries were invoiced appropriately
        # and the unrelated entries were untouched
        entries = timepiece.Entry.objects.all()
        invoiced = entries.filter(status='invoiced')
        for entry in invoiced:
            self.assertEqual(entry.invoice_id, invoice.id)
        approved = entries.filter(status='approved')
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0].invoice_id, None)
