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
