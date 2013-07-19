import datetime
from decimal import Decimal

from django.contrib.auth.models import Permission
from django.utils import timezone

from timepiece import utils
from timepiece.tests import factories
from timepiece.tests.base import TimepieceDataTestCase, ViewTestMixin

from ..models import Project


__all__ = ['TestCreateProjectView', 'TestDeleteProjectView',
        'TestProjectListView', 'TestProjectTimesheetView']


class TestCreateProjectView(ViewTestMixin, TimepieceDataTestCase):
    url_name = 'create_project'
    template_name = 'timepiece/project/create_edit.html'

    def setUp(self):
        self.user = factories.UserFactory.create()
        self.perm = Permission.objects.get(codename='add_project')
        self.user.user_permissions.add(self.perm)
        self.login_user(self.user)

    @property
    def post_data(self):
        return {
            'name': 'Project',
            'business_1': factories.BusinessFactory.create().pk,
            'point_person': factories.SuperuserFactory.create().pk,
            'activity_group': factories.ActivityGroupFactory.create().pk,
            'type': factories.TypeAttributeFactory.create().pk,
            'status': factories.StatusAttributeFactory.create().pk,
            'description': 'a project...',
        }

    def test_get_no_permission(self):
        """Permission is required to create a project."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)
        self.assertEquals(Project.objects.count(), 0)

    def test_post_no_permission(self):
        """Permission is required to create a project."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertRedirectsToLogin(response)
        self.assertEquals(Project.objects.count(), 0)

    def test_get(self):
        """GET should return the page with an unbound form."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)

    def test_post_valid(self):
        """POST should create a new project."""
        data = self.post_data
        response = self._post(data=data)
        self.assertEquals(Project.objects.count(), 1)
        project = Project.objects.get()
        self.assertRedirectsNoFollow(response, project.get_absolute_url())


class TestDeleteProjectView(ViewTestMixin, TimepieceDataTestCase):
    url_name = 'delete_project'
    template_name = 'timepiece/delete_object.html'

    def setUp(self):
        self.user = factories.UserFactory.create()
        self.perm = Permission.objects.get(codename='delete_project')
        self.user.user_permissions.add(self.perm)
        self.login_user(self.user)

        self.obj = factories.ProjectFactory.create()

        self.url_kwargs = {'project_id': self.obj.pk}

    def test_get_no_permission(self):
        """Permission is required to delete a project."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)
        self.assertEquals(Project.objects.count(), 1)

    def test_post_no_permission(self):
        """Permission is required to delete a project."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertRedirectsToLogin(response)
        self.assertEquals(Project.objects.count(), 1)

    def test_get(self):
        """GET should return a confirmation page."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object'], self.obj)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(Project.objects.count(), 1)

    def test_post(self):
        """POST should delete the project."""
        response = self._post()
        self.assertEquals(Project.objects.count(), 0)


class TestProjectListView(ViewTestMixin, TimepieceDataTestCase):
    url_name = 'list_projects'
    template_name = 'timepiece/projects/list.html'

    def setUp(self):
        self.user = factories.UserFactory.create()
        self.super_user = factories.SuperuserFactory.create()

        self.statuses = []
        self.statuses.append(factories.StatusAttributeFactory.create(label='1'))
        self.statuses.append(factories.StatusAttributeFactory.create(label='2'))
        self.statuses.append(factories.StatusAttributeFactory.create(label='3'))
        self.statuses.append(factories.StatusAttributeFactory.create(label='4'))
        self.statuses.append(factories.StatusAttributeFactory.create(label='5'))

        self.projects = []
        self.projects.append(factories.ProjectFactory.create(name='a',
                description='a', status=self.statuses[0]))
        self.projects.append(factories.ProjectFactory.create(name='b',
                description='a', status=self.statuses[0]))
        self.projects.append(factories.ProjectFactory.create(name='c',
                description='b', status=self.statuses[1]))
        self.projects.append(factories.ProjectFactory.create(name='c',
                description='d', status=self.statuses[2]))
        self.projects.append(factories.ProjectFactory.create(name='d',
                description='e', status=self.statuses[3]))

    def testUserPermission(self):
        """Regular users should be redirected to the login page.

        As written, this test could fail to detect a problem if
            1) the user is allowed to see the page, and
            2) there is only one project in the database.
        In that situation, a redirect will be issued to the individual
        project view page.

        """
        self.login_user(self.user)
        response = self._get()
        self.assertEquals(response.status_code, 302)

    def testAddPermissionToUser(self):
        """Users with view_project permission should see the project list view.

        """
        perm = Permission.objects.filter(codename__exact='view_project')
        self.user.user_permissions = perm
        self.user.save()
        self.login_user(self.user)
        response = self._get(follow=True)

        self.assertEqual(response.status_code, 200)
        if (hasattr(response, 'redirect_chain')
                and len(response.redirect_chain) > 0):
            self.assertTemplateUsed(response, 'timepiece/project/view.html')

    def testSuperUserPermission(self):
        """Super users should be able to see the project list view."""
        self.login_user(self.super_user)
        response = self._get(follow=True)

        self.assertEqual(response.status_code, 200)
        if (hasattr(response, 'redirect_chain')
                and len(response.redirect_chain) > 0):
            self.assertTemplateUsed(response, 'timepiece/project/view.html')

    def testNoSearch(self):
        """Tests when no query string or status is searched for.

        Response should contain full project list. If only one project, user
        should be redirected to individual project page.

        """
        self.login_user(self.super_user)
        data = {}
        response = self._get(data=data, follow=True)

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
        self.login_user(self.super_user)
        query = 'b'
        data = {'search': query}
        response = self._get(data=data, follow=True)

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
        self.login_user(self.super_user)
        status = self.statuses[2].pk
        data = {'status': status}
        response = self._get(data=data, follow=True)

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
        self.login_user(self.super_user)

        status = self.statuses[0].pk
        query = 'a'
        data = {'search': query, 'status': status}
        response = self._get(data=data, follow=True)

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
        self.login_user(self.super_user)

        total = 0
        for s in self.statuses:
            status = s.pk
            data = {'status': str(status)}
            response = self._get(data=data, follow=True)
            if (hasattr(response, 'redirect_chain')
                    and len(response.redirect_chain) > 0):
                total += 1
            else:
                total += len(response.context['projects'])
        correct_total = len(self.projects)
        self.assertEqual(total, correct_total)


class TestProjectTimesheetView(ViewTestMixin, TimepieceDataTestCase):
    url_name = 'view_project_timesheet'

    def setUp(self):
        super(TestProjectTimesheetView, self).setUp()
        self.p1 = factories.BillableProjectFactory.create(name='1')
        self.p2 = factories.NonbillableProjectFactory.create(name='2')
        self.p4 = factories.BillableProjectFactory.create(name='4')
        self.p3 = factories.NonbillableProjectFactory.create(name='1')
        self.url_args = (self.p1.pk,)

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

    def testNoPermission(self):
        self.login_user(self.user)
        self.make_entries()
        response = self._get()
        self.assertEqual(response.status_code, 302)

    def testNoProject(self):
        self.login_user(self.superuser)
        response = self._get(url_args=(999,))
        self.assertEqual(response.status_code, 404)

    def testEmptyProjectTimesheet(self):
        """
        The project timesheet should be empty if there are no entries, or a
        month has been selected for which there are no entries
        """
        self.login_user(self.superuser)

        def verify_empty(response):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['project'], self.p1)
            self.assertEqual(list(response.context['entries']), [])
        response = self._get()
        verify_empty(response)
        self.make_entries()
        data = {
            'year': 2011,
            'month': 4,
        }
        response = self._get(data=data)
        verify_empty(response)

    def testCurrentProjectTimesheet(self):
        self.login_user(self.superuser)
        self.make_entries()
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['project'], self.p1)
        self.assertEqual(len(response.context['entries']), 1)
        self.assertEqual(response.context['total'], Decimal(1))
        user_entry = response.context['user_entries'][0]
        self.assertEqual(user_entry['user__last_name'], self.user.last_name)
        self.assertEqual(user_entry['user__first_name'], self.user.first_name)
        self.assertEqual(user_entry['sum'], Decimal(1))

    def testOldProjectTimesheet(self):
        self.login_user(self.superuser)
        self.make_entries()
        data = {
            'year': 2011,
            'month': 1,
        }
        response = self._get(data=data)
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
        self.login_user(self.superuser)
        self.make_entries()
        response = self._get(url_args=(self.p2.pk,))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['project'], self.p2)
        self.assertEqual(len(response.context['entries']), 1)
        self.assertEqual(response.context['total'], Decimal(1))
        user_entry = response.context['user_entries'][0]
        self.assertEqual(user_entry['user__last_name'], self.user.last_name)
        self.assertEqual(user_entry['user__first_name'], self.user.first_name)
        self.assertEqual(user_entry['sum'], Decimal(1))

    def test_project_csv(self):
        self.login_user(self.superuser)
        self.make_entries()
        response = self._get(url_name='view_project_timesheet_csv',
                url_args=(self.p1.pk,))
        self.assertEqual(response.status_code, 200)
        data = dict(response.items())
        self.assertEqual(data['Content-Type'], 'text/csv')
        disposition = data['Content-Disposition']
        self.assertTrue(disposition.startswith('attachment; filename='))
        contents = response.content.splitlines()
        headers = contents[0].split(',')
        # Assure user's comments are not included.
        self.assertTrue('comments' not in headers)
