from django.core.urlresolvers import reverse

from timepiece.models import ProjectRelationship
from timepiece.tests.base import TimepieceDataTestCase


class ProjectTestCase(TimepieceDataTestCase):
    
    def test_remove_contact(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.login(username=self.user.username, password='abc')
        self.assertEquals(self.project.contacts.all().count(), 1)
        url = reverse('remove_contact_from_project', args=(self.project.pk, self.contact.pk,))
        response = self.client.get(url,{'next': '/'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(self.project.contacts.all().count(), 0)
        
    def test_add_contact(self):
        self.user.is_superuser = True
        self.user.save()
        
        self.client.login(username=self.user.username, password='abc')
        ProjectRelationship.objects.all().delete()
        self.assertEquals(self.project.contacts.all().count(), 0)
        url = reverse('add_contact_to_project', args=(self.project.pk,))
        response = self.client.post(url,{
            'contact': self.contact.pk,
        })
        self.assertEquals(response.status_code, 302)
        self.assertEquals(self.project.contacts.all().count(), 1)
