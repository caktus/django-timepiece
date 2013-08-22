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
        self.permissions = [Permission.objects.get(codename='add_project')]
        self.user = factories.UserFactory(permissions=self.permissions)
        self.login_user(self.user)

        self.post_data = {
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
        self.permissions = [Permission.objects.get(codename='delete_project')]
        self.user = factories.UserFactory(permissions=self.permissions)
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
    template_name = 'timepiece/project/list.html'

    def setUp(self):
        self.permissions = [Permission.objects.get(codename='view_project')]
        self.user = factories.UserFactory(permissions=self.permissions)
        self.login_user(self.user)

    def test_get_no_permission(self):
        """Permission is required to view the project list."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)

    def test_list_all(self):
        """If no filters are provided, all projects should be listed."""
        projects = [factories.ProjectFactory() for i in range(3)]
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['projects'].count(),
                Project.objects.count())

    def test_list_none(self):
        """Page should render even if there are no projects."""
        Project.objects.all().delete()
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['projects'].count(), 0)

    def test_list_one(self):
        """If there is only one project, and no search query, page should render."""
        project = factories.ProjectFactory()
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['projects'].count(), 1)

    def test_one_result(self):
        """If there is only one search result, user should be redirected."""
        project = factories.ProjectFactory()
        response = self._get(get_kwargs={'status': project.status.pk})
        self.assertRedirectsNoFollow(response, project.get_absolute_url())

    def test_filter_name(self):
        """User should be able to filter by search query and status."""
        project = factories.ProjectFactory(name='hello')
        other_project = factories.ProjectFactory()
        response = self._get(get_kwargs={'search': 'ello'})
        self.assertRedirectsNoFollow(response, project.get_absolute_url())

    def test_filter_description(self):
        """User should be able to filter by search query and status."""
        project = factories.ProjectFactory(description='hello')
        other_project = factories.ProjectFactory()
        response = self._get(get_kwargs={'search': 'ello'})
        self.assertRedirectsNoFollow(response, project.get_absolute_url())

    def test_filter_status(self):
        """User should be able to filter by search query and status."""
        project = factories.ProjectFactory()
        other_project = factories.ProjectFactory()
        response = self._get(get_kwargs={'status': project.status.pk})
        self.assertRedirectsNoFollow(response, project.get_absolute_url())

    def test_filter_query_and_status(self):
        """User should be able to filter by search query and status."""
        project = factories.ProjectFactory(name='hello')
        other_project1 = factories.ProjectFactory(description='hello')
        other_project2 = factories.ProjectFactory(status=project.status)
        get_kwargs = {'status': project.status.pk, 'search': 'ello'}
        response = self._get(get_kwargs=get_kwargs)
        self.assertRedirectsNoFollow(response, project.get_absolute_url())


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
