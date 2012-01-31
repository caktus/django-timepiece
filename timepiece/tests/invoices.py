import datetime
import random

from django.core.urlresolvers import reverse

from timepiece import models as timepiece
from timepiece.tests.base import TimepieceDataTestCase


class InvoiceViewPreviousTestCase(TimepieceDataTestCase):
    def setUp(self):
        super(InvoiceViewPreviousTestCase, self).setUp()
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username=self.user.username, password='abc')
        # Make some projects and entries for invoice creation
        self.num_entries = 20
        self.log_many()
        self.create_invoice()
        self.create_invoice(self.project2, status='not-invoiced')

    def log_many(self):
        self.project = self.create_project(billable=True)
        self.project2 = self.create_project(billable=True)
        projects = (self.project, self.project2)
        project = self.project2
        start = datetime.datetime(2011, 1, 1, 0, 0, 0)
        for index in xrange(0, self.num_entries):
            start += datetime.timedelta(hours=(5 * index))
            # Alternate projects
            if project == self.project2:
                project = self.project
            else:
                project = self.project2
            self.log_time(start=start, status='approved', project=project)

    def create_invoice(self, project=None, status='invoiced'):
        if not project:
            project = self.project
        to_date = datetime.datetime(2011, 1, 31)
        args = [project.id, to_date.strftime('%Y-%m-%d')]
        url = reverse('confirm_invoice_project', args=args)
        params = {
            'number': random.randint(999, 9999),
            'status': status,
        }
        response = self.client.post(url, params)

    def get_invoice(self):
        invoices = timepiece.EntryGroup.objects.all()
        return random.choice(invoices)

    def get_entry(self, invoice):
        entries = invoice.entries.all()
        return random.choice(entries)

    def test_previous_invoice_list(self):
        url = reverse('list_invoices')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        invoices = response.context['invoices']
        self.assertEqual(len(invoices), 2)

    def test_invoice_detail(self):
        invoices = timepiece.EntryGroup.objects.all()
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
        contents = response.content.splitlines()
        # TODO: Possibly find a meaningful way to test contents

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
        url = reverse('edit_invoice', kwargs={'pk': invoice.id})
        status = 'invoiced' if invoice.status != 'invoiced' else 'not-invoiced'
        params = {
            'number': invoice.number + 1,
            'status': status,
            'comments': 'Comments',
        }
        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 302)
        new_invoice = timepiece.EntryGroup.objects.get(pk=invoice.id)
        self.assertEqual(invoice.number + 1, new_invoice.number)
        self.assertTrue(invoice.status != new_invoice.status)
        self.assertEqual(new_invoice.comments, 'Comments')

    def test_invoice_edit_bad_post(self):
        invoice = self.get_invoice()
        url = reverse('edit_invoice', args=[invoice.id])
        params = {
            'number': 'String',
            'status': 'not_in_choices',
        }
        response = self.client.post(url, params)
        err_msg = 'Enter a whole number.'
        self.assertFormError(response, 'invoice_form', 'number', err_msg)
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
        self.assertFalse(timepiece.EntryGroup.objects.filter(pk=invoice.id))
        entries = timepiece.Entry.objects.filter(pk__in=entry_ids)
        for entry in entries:
            self.assertEqual(entry.status, 'approved')

    def test_invoice_delete_cancel(self):
        invoice = self.get_invoice()
        url = reverse('delete_invoice', args=[invoice.id])
        response = self.client.post(url, {'cancel': 'cancel'})
        self.assertEqual(response.status_code, 302)
        # Canceled out so the invoice was not deleted
        self.assertTrue(timepiece.EntryGroup.objects.get(pk=invoice.id))

    def test_invoice_delete_bad_args(self):
        invoice = self.get_invoice()
        entry_ids = [entry.pk for entry in invoice.entries.all()]
        url = reverse('delete_invoice', args=[1232345345])
        response = self.client.post(url, {'delete': 'delete'})
        self.assertEqual(response.status_code, 404)

    def test_rm_invoice_entry_get(self):
        invoice = self.get_invoice()
        entry = self.get_entry(invoice)
        url = reverse('remove_invoice_entry', args=[invoice.id, entry.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['invoice'], invoice)
        self.assertEqual(response.context['entry'], entry)

    def test_rm_invoice_entry_get_bad_id(self):
        invoice = self.get_invoice()
        entry = self.get_entry(invoice)
        url = reverse('remove_invoice_entry', args=[invoice.id, 999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        url = reverse('remove_invoice_entry', args=[9999, entry.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_rm_invoice_entry_post(self):
        invoice = self.get_invoice()
        entry = self.get_entry(invoice)
        url = reverse('remove_invoice_entry', args=[invoice.id, entry.id])
        response = self.client.post(url, {'submit': ''})
        self.assertEqual(response.status_code, 302)
        new_invoice = timepiece.EntryGroup.objects.get(pk=invoice.pk)
        rm_entry = new_invoice.entries.filter(pk=entry.id)
        self.assertFalse(rm_entry)
        new_entry = timepiece.Entry.objects.get(pk=entry.pk)
        self.assertEqual(new_entry.status, 'approved')
        self.assertEqual(new_entry.entry_group, None)


class InvoiceCreateTestCase(TimepieceDataTestCase):
    def setUp(self):
        super(InvoiceCreateTestCase, self).setUp()
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

    def make_hourgroups(self):
        """
        Make several hour groups, one for each activity, and one that contains
        all activities to check for hour groups with multiple activities.
        """
        all_activities = timepiece.Activity.objects.all()
        for activity in all_activities:
            hg = timepiece.HourGroup.objects.create(name=activity.name)
            hg.activities.add(activity)
            hg.save()
        hg = timepiece.HourGroup.objects.create(name='all')
        activity_ids = [activity.id for activity in all_activities]
        hg.activities.add(*activity_ids)
        hg.save()
    
    def test_invoice_create(self):
        """
        Verify that only billable projects appear on the create invoice and
        that the links have accurate date information
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

    def test_invoice_create_requires_to(self):
        """Verify that create invoice links are blank without a to date"""
        url = reverse('invoice_projects')
        params = {'to_date': ''}
        response = self.client.get(url, params)
        # The number of projects should be 1 because entry3 has billable=False
        num_project_totals = len(response.context['project_totals'])
        self.assertEquals(num_project_totals, 0)

    def test_invoice_create_with_from(self):
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

    def test_invoice_confirm_view(self):
        to_date = datetime.datetime(2011, 1, 31)
        args = [self.project_billable.id, to_date.strftime('%Y-%m-%d')]
        url = reverse('confirm_invoice_project', args=args)
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
        url = reverse('confirm_invoice_project', args=args)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        from_date_str = response.context['from_date'].strftime('%Y %m %d')
        to_date_str = response.context['to_date'].strftime('%Y %m %d')
        self.assertEqual(from_date_str, '2011 01 01')
        self.assertEqual(to_date_str, '2011 01 31')

    def test_invoice_confirm_totals(self):
        """Verify that the per activity totals are valid."""
        # Make a few extra entries to test per activity totals
        start = datetime.datetime(2011, 1, 1, 8, 0, 0)
        end = datetime.datetime(2011, 1, 1, 12, 0, 0)
        activity = self.create_activity(data={'name': 'activity1'})
        for num in xrange(0, 4):
            new_entry = self.create_entry({
                'user': self.user,
                'project': self.project_billable,
                'start_time': start - datetime.timedelta(days=num),
                'end_time': end - datetime.timedelta(days=num),
                'status': 'approved',
                'activity': activity,
            })
        self.make_hourgroups()
        to_date = datetime.datetime(2011, 1, 31)
        args = [self.project_billable.id, to_date.strftime('%Y-%m-%d')]
        url = reverse('confirm_invoice_project', args=args)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        for name, hours in response.context['totals']:
            if name == 'activity1':
                self.assertEqual(hours, 16)
            elif name == 'Total' or name == 'all':
                self.assertEqual(hours, 24)
            else:
                self.assertEqual(hours, 4)

    def test_invoice_confirm_bad_args(self):
        # A year/month/project with no entries should raise a 404
        args = [self.project_billable.id, '2008-01-13']
        url = reverse('confirm_invoice_project', args=args)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        # A year/month with bad/overflow values should raise a 404
        args = [self.project_billable.id, '9999-13-01']
        url = reverse('confirm_invoice_project', args=args)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_make_invoice(self):
        to_date = datetime.datetime(2011, 1, 31)
        args = [self.project_billable.id, to_date.strftime('%Y-%m-%d')]
        url = reverse('confirm_invoice_project', args=args)
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
        url = reverse('confirm_invoice_project', args=args)
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

    def test_make_invoice_bad_number(self):
        to_date = datetime.datetime(2011, 1, 31)
        args = [self.project_billable.id, to_date.strftime('%Y-%m-%d')]
        url = reverse('confirm_invoice_project', args=args)
        response = self.client.post(url, {'number': 'string'})
        err_msg = 'Enter a whole number.'
        self.assertFormError(response, 'invoice_form', 'number', err_msg)
        response = self.client.post(url, {'number': None})
        self.assertFormError(response, 'invoice_form', 'number', err_msg)
