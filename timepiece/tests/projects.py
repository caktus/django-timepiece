import datetime
from decimal import Decimal

from django.core.urlresolvers import reverse

try:
    from django.utils import timezone
except ImportError:
    from timepiece import timezone

from timepiece import models as timepiece
from timepiece.tests.base import TimepieceDataTestCase
from timepiece import utils


class ProjectTestCase(TimepieceDataTestCase):

    def setUp(self):
        super(ProjectTestCase, self).setUp()
        self.p1 = self.create_project(billable=True, name='1')
        self.p2 = self.create_project(billable=False, name='2')
        self.p4 = self.create_project(billable=True, name='4')
        self.p3 = self.create_project(billable=False, name='1')
        self.url = reverse('project_time_sheet',
                           kwargs={'pk': self.p1.pk}
        )

    def make_entries(self):
        days = [
            utils.add_timezone(datetime.datetime(2011, 1, 1)),
            utils.add_timezone(datetime.datetime(2011, 1, 28)),
            utils.add_timezone(datetime.datetime(2011, 1, 31)),
            utils.add_timezone(datetime.datetime(2011, 2, 1)),
            timezone.now(),
        ]
        self.log_time(project=self.p1, start=days[0], delta=(1, 0))
        self.log_time(project=self.p2, start=days[0], delta=(1, 0))
        self.log_time(project=self.p1, start=days[1], delta=(1, 0))
        self.log_time(project=self.p3, start=days[1], delta=(1, 0))
        self.log_time(project=self.p1, user=self.user2, start=days[2],
                      delta=(1, 0))
        self.log_time(project=self.p2, start=days[2], delta=(1, 0))
        self.log_time(project=self.p1, start=days[3], delta=(1, 0))
        self.log_time(project=self.p3, start=days[3], delta=(1, 0))
        self.log_time(project=self.p1, start=days[4], delta=(1, 0))
        self.log_time(project=self.p2, start=days[4], delta=(1, 0))

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
        response = self.client.post(url, {
            'user_0': self.user.get_full_name(),  # Can be anything
            'user_1': self.user.pk  # Must be pk
        })
        self.assertEquals(response.status_code, 302)
        self.assertEquals(self.project.users.all().count(), 1)

        timepiece.ProjectRelationship.objects.all().delete()
        self.assertEquals(self.project.users.all().count(), 0)
        response = self.client.post(url, {
            'user_0': '',  # Can be anything
            'user_1': self.user.pk  # Must be pk
        })
        self.assertEquals(response.status_code, 302)
        self.assertEquals(self.project.users.all().count(), 1)

    def testNoPermission(self):
        self.client.login(username='user', password='abc')
        self.make_entries()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def testNoProject(self):
        self.client.login(username='superuser', password='abc')
        response = self.client.get(reverse('project_time_sheet', args=(999, )))
        self.assertEqual(response.status_code, 404)

    def testEmptyProjectTimesheet(self):
        """
        The project timesheet should be empty if there are no entries, or a
        month has been selected for which there are no entries
        """
        self.client.login(username='superuser', password='abc')

        def verify_empty(response):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['project'], self.p1)
            self.assertEqual(list(response.context['entries']), [])
        response = self.client.get(self.url)
        verify_empty(response)
        self.make_entries()
        data = {
            'year': 2011,
            'month': 4,
        }
        response = self.client.get(self.url, data)
        verify_empty(response)

    def testCurrentProjectTimesheet(self):
        self.client.login(username='superuser', password='abc')
        self.make_entries()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['project'], self.p1)
        self.assertEqual(len(response.context['entries']), 1)
        self.assertEqual(response.context['total'], Decimal(1))
        user_entry = response.context['user_entries'][0]
        self.assertEqual(user_entry['user__last_name'], self.user.last_name)
        self.assertEqual(user_entry['user__first_name'], self.user.first_name)
        self.assertEqual(user_entry['sum'], Decimal(1))

    def testOldProjectTimesheet(self):
        self.client.login(username='superuser', password='abc')
        self.make_entries()
        data = {
            'year': 2011,
            'month': 1,
        }
        response = self.client.get(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['project'], self.p1)
        self.assertEqual(len(response.context['entries']), 3)
        self.assertEqual(response.context['total'], Decimal(3))
        user_entry0 = response.context['user_entries'][0]
        user_entry1 = response.context['user_entries'][1]
        self.assertEqual(user_entry0['user__last_name'], self.user.last_name)
        self.assertEqual(user_entry0['user__first_name'], self.user.first_name)
        self.assertEqual(user_entry0['sum'], Decimal(2))
        self.assertEqual(user_entry1['user__last_name'], self.user2.last_name)
        self.assertEqual(user_entry1['user__first_name'],
                         self.user2.first_name
        )
        self.assertEqual(user_entry1['sum'], Decimal(1))

    def testOtherProjectTimesheet(self):
        self.client.login(username='superuser', password='abc')
        self.make_entries()
        response = self.client.get(reverse('project_time_sheet',
                                           args=(self.p2.pk, ))
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['project'], self.p2)
        self.assertEqual(len(response.context['entries']), 1)
        self.assertEqual(response.context['total'], Decimal(1))
        user_entry = response.context['user_entries'][0]
        self.assertEqual(user_entry['user__last_name'], self.user.last_name)
        self.assertEqual(user_entry['user__first_name'], self.user.first_name)
        self.assertEqual(user_entry['sum'], Decimal(1))

    def test_project_csv(self):
        self.client.login(username='superuser', password='abc')
        self.make_entries()
        response = self.client.get(reverse('export_project_time_sheet',
                                           args=[self.p1.id])
        )
        self.assertEqual(response.status_code, 200)
        data = dict(response.items())
        self.assertEqual(data['Content-Type'], 'text/csv')
        disposition = data['Content-Disposition']
        self.assertTrue(disposition.startswith('attachment; filename='))
        contents = response.content.splitlines()
        headers = contents[0].split(',')
        # Assure user's comments are not included.
        self.assertTrue('comments' not in headers)
