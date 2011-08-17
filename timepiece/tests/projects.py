import datetime
from dateutil import relativedelta
import urllib
import re

from django.core.urlresolvers import reverse

from timepiece.models import ProjectRelationship
from timepiece.tests.base import TimepieceDataTestCase


class ProjectTestCase(TimepieceDataTestCase):
    invoice_to_date = datetime.datetime.now().date()
    invoice_from_date = datetime.datetime.now().date()
    
    def test_remove_user(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username=self.user.username, password='abc')
        self.assertEquals(self.project.users.all().count(), 1)
        url = reverse('remove_user_from_project', args=(self.project.pk, self.user.pk,))
        response = self.client.get(url,{'next': '/'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(self.project.users.all().count(), 0)
        
    def test_add_user(self):
        self.user.is_superuser = True
        self.user.save()
        
        self.client.login(username=self.user.username, password='abc')
        ProjectRelationship.objects.all().delete()
        self.assertEquals(self.project.users.all().count(), 0)
        url = reverse('add_user_to_project', args=(self.project.pk,))
        response = self.client.post(url,{
            'user': self.user.pk,
        })
        self.assertEquals(response.status_code, 302)
        self.assertEquals(self.project.users.all().count(), 1)
        
    def test_invoice_list(self):
        """
        Verify that only billable projects appear on the invoice list and that
        the links have accurate date information
        """
        self.user.is_superuser = True
        self.user.save()        
        self.client.login(username=self.user.username, password='abc')
        now = datetime.datetime.now() - datetime.timedelta(hours=10)
        backthen = now - datetime.timedelta(hours=20)        
        project_billable = self.create_project(billable=True)
        project_non_billable = self.create_project(billable=False)
        entry1 = self.create_entry({
            'user': self.user,
            'project': project_billable,
            'start_time': backthen,
            'end_time': now,
            'status': 'approved',
        })
        entry2 = self.create_entry({
            'user': self.user,
            'project': project_non_billable,
            'start_time': entry1.start_time + datetime.timedelta(hours=11),
            'end_time': entry1.end_time + datetime.timedelta(hours=15),
            'status': 'approved',
        })
        url = reverse('invoice_projects')
        response = self.client.get(url)        
        #The number of projects should be 1 because entry2 has billable=False
        num_project_totals = len(response.context['project_totals'])
        self.assertEquals(num_project_totals, 1)
        #verify that the date on the mark as invoiced links are correct
        correct_begin = entry1.start_time + relativedelta.relativedelta(day = 1)
        correct_end = entry1.end_time + relativedelta.relativedelta(months =+ 1, day = 1)
        self.invoice_from_date = response.context['from_date']
        self.invoice_to_date = response.context['to_date']
    
    def test_mark_invoice(self):
        """
        Test that billable entries create a valid link to mark them as invoiced.
        """
        self.user.is_superuser = True
        self.user.save()        
        self.client.login(username=self.user.username, password='abc')
        now = datetime.datetime.now() - datetime.timedelta(hours=10)
        backthen = now - datetime.timedelta(hours=20)        
        project_billable = self.create_project(billable=True)
        entry1 = self.create_entry({
            'user': self.user,
            'project': project_billable,
            'start_time': backthen,
            'end_time': now,
            'status': 'approved',
        })
        url = reverse('time_sheet_change_status', kwargs = {'action':'invoice'})
        data = {
            'project': project_billable.pk,
            'to_date': self.invoice_to_date,
            'from_date': self.invoice_from_date,
        }
        #Mark as invoiced link links to a page with correct times in the URL 
        response = self.client.get(url, data)
        self.assertEquals(response.status_code, 200)
        returned_dates = re.findall('=(\d\d\d\d-\d\d-\d\d)&?',response.context['return_url'])
        self.assertEqual(returned_dates[0], self.invoice_from_date.strftime('%Y-%m-%d'))
        self.assertEqual(returned_dates[1], self.invoice_to_date.strftime('%Y-%m-%d'))
        #Test that the "Yes" link on the mark as invoiced page redirects to
        #invoice projects with the correct date
        get_str = urllib.urlencode({
            'from_date': self.invoice_from_date,
            'to_date': self.invoice_to_date,
        })
        return_url = url + '?%s' % get_str
        data = {'do_action': 'Yes'}        
        response = self.client.post(return_url,data, follow=True)
        self.assertEqual(response.context['from_date'], self.invoice_from_date)
        self.assertEqual(response.context['to_date'], self.invoice_to_date)
        
