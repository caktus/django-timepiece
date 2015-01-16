from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse
from django.test import TestCase

from timepiece.tests import factories
from timepiece.tests.base import ViewTestMixin
from timepiece.crm.models import ProjectRelationship


class RelationshipTestBase(TestCase):

    def setUp(self):
        super(RelationshipTestBase, self).setUp()
        self.user = factories.User()
        self.permissions = [Permission.objects.get(codename=n) for n in
                self.perm_names]
        self.user.user_permissions.add(*self.permissions)
        self.login_user(self.user)

        self.project = factories.Project()


class TestAddProjectToUser(ViewTestMixin, RelationshipTestBase):
    url_name = 'create_relationship'
    perm_names = ['add_projectrelationship']

    @property
    def get_kwargs(self):
        return {'user_id': self.user.pk}

    def _data(self):
        return {'project_1': self.project.pk}

    def test_other_methods(self):
        """Add Project Relationship requires POST."""
        for method in (self.client.get, self.client.head, self.client.put,
                self.client.delete):
            response = method(self._url())
            self.assertEquals(response.status_code, 405, '{method} request '
                    'did not have expected code: {actual} instead of '
                    '{expected}'.format(method=method,
                    actual=response.status_code, expected=405))
            self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_permission(self):
        """Permission is required to add a project relationship."""
        self.user.user_permissions.remove(*self.permissions)

        response = self._post()
        self.assertEquals(response.status_code, 302)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_bad_user_id(self):
        """Bad user id should return a 404 response."""
        response = self._post(get_kwargs={'user_id': '12345'})
        self.assertEquals(response.status_code, 404)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_bad_project_id(self):
        """Bad project id should cause no change."""
        response = self._post(data={'project_1': '12345'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_add_again(self):
        """Adding project again should have no effect."""
        rel = factories.ProjectRelationship(project=self.project,
                user=self.user)

        response = self._post(data=self._data())
        self.assertEquals(response.status_code, 302)
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)

    def test_redirect_to_dashboard(self):
        """Adding a relationship should redirect to the dashboard by default."""
        response = self._post(data=self._data())
        self.assertRedirectsNoFollow(response, reverse('dashboard'))
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)

    def test_redirect_to_next(self):
        """Adding a relationship should redirect to next url if available."""
        get_kwargs = self.get_kwargs
        get_kwargs.update({'next': '/hello'})
        response = self._post(data=self._data(), get_kwargs=get_kwargs)
        self.assertRedirectsNoFollow(response, '/hello')
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)


class TestAddUserToProject(ViewTestMixin, RelationshipTestBase):
    url_name = 'create_relationship'
    perm_names = ['change_projectrelationship', 'add_projectrelationship']

    @property
    def get_kwargs(self):
        return {'project_id': self.project.pk}

    def _data(self):
        return {'user_1': self.user.pk}

    def test_other_methods(self):
        """Add Project Relationship requires POST."""
        for method in (self.client.get, self.client.head, self.client.put,
                self.client.delete):
            response = method(self._url())
            self.assertEquals(response.status_code, 405, '{method} request '
                    'did not have expected code: {actual} instead of '
                    '{expected}'.format(method=method,
                    actual=response.status_code, expected=405))
            self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_permission(self):
        """Permission is required to add a project relationship."""
        self.user.user_permissions.remove(*self.permissions)

        response = self._post()
        self.assertEquals(response.status_code, 302)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_bad_project_id(self):
        """Bad project id should return a 404 response."""
        response = self._post(get_kwargs={'project_id': '12345'})
        self.assertEquals(response.status_code, 404)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_bad_user_id(self):
        """Bad user id should cause no change."""
        response = self._post(data={'user_1': '12345'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_add_again(self):
        """Adding user again should have no effect."""
        rel = factories.ProjectRelationship(project=self.project,
                user=self.user)

        response = self._post(data=self._data())
        self.assertEquals(response.status_code, 302)
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)

    def test_redirect_to_dashboard(self):
        """Adding a relationship hould redirect to the dashboard by default."""
        response = self._post(data=self._data())
        self.assertRedirectsNoFollow(response, reverse('dashboard'))
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)

    def test_redirect_to_next(self):
        """Adding a relationship should redirect to next url if available."""
        get_kwargs = self.get_kwargs
        get_kwargs.update({'next': '/hello'})
        response = self._post(data=self._data(), get_kwargs=get_kwargs)
        self.assertRedirectsNoFollow(response, '/hello')
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)


class TestEditRelationship(ViewTestMixin, RelationshipTestBase):
    url_name = 'edit_relationship'
    perm_names = ['change_projectrelationship']

    @property
    def get_kwargs(self):
        return {'project_id': self.project.pk, 'user_id': self.user.pk}

    def _data(self):
        return {'types': [self.rel_type1.pk, self.rel_type2.pk]}

    def setUp(self):
        super(TestEditRelationship, self).setUp()
        self.relationship = factories.ProjectRelationship(
            project=self.project, user=self.user)
        self.rel_type1 = factories.RelationshipType()
        self.rel_type2 = factories.RelationshipType()

    def test_permission(self):
        """Permission is required to edit a project relationship."""
        self.user.user_permissions.remove(*self.permissions)

        for method in (self._get, self._post):
            response = method()
            self.assertEquals(response.status_code, 302)

    def test_bad_user_id(self):
        """Bad user id should return a 404 response."""
        get_kwargs = {'user_id': '12345', 'project_id': self.project.pk}

        for method in (self._get, self._post):
            response = method(get_kwargs=get_kwargs)
            self.assertEquals(response.status_code, 404)
            rel = ProjectRelationship.objects.get()
            self.assertEquals(rel, self.relationship)

    def test_bad_project_id(self):
        """Bad project id should return a 404 response."""
        get_kwargs = {'user_id': self.user.pk, 'project_id': '12345'}

        for method in (self._get, self._post):
            response = method(get_kwargs=get_kwargs)
            self.assertEquals(response.status_code, 404)
            rel = ProjectRelationship.objects.get()
            self.assertEquals(rel, self.relationship)

    def test_non_existant_relationship(self):
        """Should return 404 response."""
        self.relationship.delete()

        for method in (self._get, self._post):
            response = method()
            self.assertEquals(response.status_code, 404)
            self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_get(self):
        """GET request should return form with bound data."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        context = response.context
        form = context['form']
        self.assertEquals(ProjectRelationship.objects.get(), self.relationship)
        self.assertEqual(context['object'], self.relationship)
        self.assertFalse(form.is_bound)
        self.assertEquals(form.instance, self.relationship)

    def test_redirect_to_project_page(self):
        """Editing a relationship should redirect to project by default."""
        project_url = reverse('view_project', args=(self.project.pk,))

        response = self._post(data=self._data())
        self.assertRedirectsNoFollow(response, project_url)
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)
        self.assertEquals(rel.types.count(), 2)
        self.assertTrue(self.rel_type1 in rel.types.all())
        self.assertTrue(self.rel_type2 in rel.types.all())

    def test_redirect_to_next(self):
        """Editing a relationship should redirect to next url if available."""
        get_kwargs = self.get_kwargs
        get_kwargs.update({'next': '/hello'})
        response = self._post(data=self._data(), get_kwargs=get_kwargs)
        self.assertRedirectsNoFollow(response, '/hello')
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)
        self.assertEquals(rel.types.count(), 2)
        self.assertTrue(self.rel_type1 in rel.types.all())
        self.assertTrue(self.rel_type2 in rel.types.all())


class TestDeleteRelationship(ViewTestMixin, RelationshipTestBase):
    url_name = 'delete_relationship'
    perm_names = ['delete_projectrelationship']

    def setUp(self):
        super(TestDeleteRelationship, self).setUp()
        self.relationship = factories.ProjectRelationship(
            project=self.project, user=self.user)

    @property
    def get_kwargs(self):
        return {'project_id': self.project.pk, 'user_id': self.user.pk}

    def test_get_no_delete(self):
        """Remove Project Relationship renders but doesn't delete on GET"""
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ProjectRelationship.objects.count(), 1)

    def test_permission(self):
        """Permission is required to delete a project relationship."""
        self.user.user_permissions.remove(*self.permissions)
        response = self._post()
        self.assertEquals(response.status_code, 302)
        self.assertEquals(ProjectRelationship.objects.count(), 1)

    def test_bad_user_id(self):
        """Bad user id should return a 404 response."""
        get_kwargs = {'user_id': '12345', 'project_id': self.project.pk}
        response = self._post(get_kwargs=get_kwargs)
        self.assertEquals(response.status_code, 404)
        self.assertEquals(ProjectRelationship.objects.count(), 1)

    def test_bad_project_id(self):
        """Bad project id should return a 404 response."""
        get_kwargs = {'user_id': self.user.pk, 'project_id': '12345'}
        response = self._post(get_kwargs=get_kwargs)
        self.assertEquals(response.status_code, 404)
        self.assertEquals(ProjectRelationship.objects.count(), 1)

    def test_non_existant_relationship(self):
        """Assure 404 is raised if the project relationship doesn't exist"""
        self.relationship.delete()
        response = self._post()
        self.assertEquals(response.status_code, 404)
        self.assertEquals(ProjectRelationship.objects.count(), 0)
