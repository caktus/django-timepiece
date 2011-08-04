import datetime
from urllib import urlencode

from django.core.urlresolvers import reverse

from timepiece.models import ProjectRelationship
from timepiece.tests.base import TimepieceDataTestCase


class ProjectTestCase(TimepieceDataTestCase):
    
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
        
    def test_invoice(self):
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

