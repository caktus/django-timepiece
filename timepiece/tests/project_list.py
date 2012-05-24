from urllib import unquote, urlencode

from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.core.urlresolvers import reverse

from timepiece.tests.base import TimepieceDataTestCase


class ProjectListTest(TimepieceDataTestCase):

    def setUp(self):
        self.url = reverse('list_projects')

        self.user = User.objects.create_user('user', 'u@a.com', 'abc')
        self.user.save()

        self.super_user = User.objects.create_user('super', 's@a.com', 'abc')
        self.super_user.is_superuser = True
        self.super_user.save()

        self.statuses = []
        self.statuses.append(self.create_project_status(data={'label': '1'}))
        self.statuses.append(self.create_project_status(data={'label': '2'}))
        self.statuses.append(self.create_project_status(data={'label': '3'}))
        self.statuses.append(self.create_project_status(data={'label': '4'}))
        self.statuses.append(self.create_project_status(data={'label': '5'}))

        self.projects = []
        self.projects.append(self.create_project(name='a',
                data={'description': 'a', 'status': self.statuses[0]}))
        self.projects.append(self.create_project(name='b',
                data={'description': 'a', 'status': self.statuses[0]}))
        self.projects.append(self.create_project(name='c',
                data={'description': 'b', 'status': self.statuses[1]}))
        self.projects.append(self.create_project(name='c',
                data={'description': 'd', 'status': self.statuses[2]}))
        self.projects.append(self.create_project(name='d',
                data={'description': 'e', 'status': self.statuses[3]}))

    def testUserPermission(self):
        """Regular users should be redirected to the login page.

        As written, this test could fail to detect a problem if
            1) the user is allowed to see the page, and
            2) there is only one project in the database.
        In that situation, a redirect will be issued to the individual
        project view page.

        """
        self.client.login(username='user', password='abc')
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 302)

    def testAddPermissionToUser(self):
        """Users with view_project permission should see the project list view.

        """
        perm = Permission.objects.filter(codename__exact='view_project')
        self.user.user_permissions = perm
        self.user.save()
        self.client.login(username='user', password='abc')
        response = self.client.get(self.url, follow=True)

        self.assertEqual(response.status_code, 200)
        if (hasattr(response, 'redirect_chain')
                and len(response.redirect_chain) > 0):
            self.assertTemplateUsed(response, 'timepiece/project/view.html')

    def testSuperUserPermission(self):
        """Super users should be able to see the project list view."""
        self.client.login(username='super', password='abc')
        response = self.client.get(self.url, follow=True)

        self.assertEqual(response.status_code, 200)
        if (hasattr(response, 'redirect_chain')
                and len(response.redirect_chain) > 0):
            self.assertTemplateUsed(response, 'timepiece/project/view.html')

    def testNoSearch(self):
        """Tests when no query string or status is searched for.

        Response should contain full project list. If only one project, user
        should be redirected to individual project page.

        """
        self.client.login(username='super', password='abc')
        data = {}
        response = self.client.get(self.url, data=data, follow=True)

        self.assertEqual(response.status_code, 200)
        correct_len = len(self.projects)
        if correct_len == 1:
            self.assertTrue(len(response.redirect_chain) > 0)
            self.assertTemplateUsed(response, 'timepiece/project/view.html')
        else:
            self.assertEqual(len(response.context['projects']), correct_len)

    def testQuerySearch(self):
        """Tests when only a query string is searched for.

        Project list should contain projects which contain the query string
        in the title or description, regardless of status. If only one
        project, user should be redirected to individual project page.

        """
        self.client.login(username='super', password='abc')
        query = 'b'
        data = {'search': query}
        response = self.client.get(self.url, data=data, follow=True)

        self.assertEqual(response.status_code, 200)
        correct_len = len([p for p in self.projects
                if query in p.name.lower() or
                query in p.description.lower()])
        if correct_len == 1:
            self.assertTrue(len(response.redirect_chain) > 0)
            self.assertTemplateUsed(response, 'timepiece/project/view.html')
        else:
            self.assertEqual(len(response.context['projects']), correct_len)

    def testStatusSearch(self):
        """Tests when only a status is searched for.

        Project list should contain all projects which have the specified
        status. If only one project, user should be redirected to individual
        project page.

        """
        self.client.login(username='super', password='abc')
        status = self.statuses[2].pk
        data = {'status': status}
        response = self.client.get(self.url, data=data, follow=True)

        self.assertEqual(response.status_code, 200)
        correct_len = len([p for p in self.projects
                if p.status.pk == status])
        if correct_len == 1:
            self.assertTrue(len(response.redirect_chain) > 0)
            self.assertTemplateUsed(response, 'timepiece/project/view.html')
        else:
            self.assertEqual(len(response.context['projects']), correct_len)

    def testQueryAndStatusSearch(self):
        """Tests when a query string and a status are searched for.

        Project list should only contain projects with the query string in the
        title or description AND with the specified status. If only one
        project, user should be redirected to individual project page.

        """
        self.client.login(username='super', password='abc')

        status = self.statuses[0].pk
        query = 'a'
        data = {'search': query, 'status': status}
        response = self.client.get(self.url, data=data, follow=True)

        self.assertEqual(response.status_code, 200)
        correct_len = len([p for p in self.projects
                if p.status.pk == status and
                (query in p.name.lower() or
                query in p.description.lower())])
        if correct_len == 1:
            self.assertTrue(len(response.redirect_chain) > 0)
            self.assertTemplateUsed(response, 'timepiece/project/view.html')
        else:
            self.assertEqual(len(response.context['projects']), correct_len)

    def testCanFindAll(self):
        """All projects should be findable by status.

        Because the status field of the Project model is required/cannot be
        null, the sum of project counts for each status should equal the
        total project count.

        """
        self.client.login(username='super', password='abc')

        total = 0
        for s in self.statuses:
            status = s.pk
            data = {'status': str(status)}
            response = self.client.get(self.url, data=data, follow=True)
            if (hasattr(response, 'redirect_chain')
                    and len(response.redirect_chain) > 0):
                total += 1
            else:
                total += len(response.context['projects'])
        correct_total = len(self.projects)
        self.assertEqual(total, correct_total)
