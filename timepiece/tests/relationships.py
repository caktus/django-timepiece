import urllib

from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse

from timepiece.models import ProjectRelationship
from timepiece.tests.base import TimepieceDataTestCase


class RelationshipTestBase(TimepieceDataTestCase):

    def setUp(self):
        self.username = self.random_string(25)
        self.password = self.random_string(25)
        self.user = self.create_user(username=self.username,
                password=self.password)
        self.permission = Permission.objects.get(codename=self.perm_name)
        self.user.user_permissions.add(self.permission)
        self.client.login(username=self.username, password=self.password)

        self.project = self.create_project()

    def _get(self, url_name=None, url_kwargs=None, *args, **kwargs):
        url_name = url_name or self.url_name
        if url_kwargs is None:
            url_kwargs = self._url_kwargs()
        url = reverse(url_name, kwargs=url_kwargs)
        return self.client.get(url, *args, **kwargs)

    def _post(self, url_name=None, url_kwargs=None, get_kwargs=None, *args,
                **kwargs):
        url_name = url_name or self.url_name
        if url_kwargs is None:
            url_kwargs = self._url_kwargs()
        url = reverse(url_name, kwargs=url_kwargs)
        if get_kwargs is not None:
            url += '?' + urllib.urlencode(get_kwargs)
        return self.client.post(url, *args, **kwargs)

    def _assertRedirectsNoFollow(self, response, url):
        self.assertEquals(response.status_code, 302)
        full_url = 'http://testserver' + url
        self.assertEquals(response._headers['location'][1], full_url)


class AddProjectToUserTestCase(RelationshipTestBase):
    url_name = 'add_project_to_user'
    perm_name = 'add_projectrelationship'

    def _url_kwargs(self):
        return {'user_id': self.user.pk}

    def _data(self):
        return {'project_1': self.project.pk}

    def test_other_methods(self):
        """Add Project Relationship requires POST."""
        url = reverse(self.url_name, kwargs=self._url_kwargs())
        for method in (self.client.get, self.client.head, self.client.options,
                self.client.put, self.client.delete):
            response = method(url)
            self.assertEquals(response.status_code, 405)
            self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_permission(self):
        """Permission is required to add a project relationship."""
        self.user.user_permissions.remove(self.permission)

        response = self._post()
        self.assertEquals(response.status_code, 302)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_bad_user_id(self):
        """Bad user id should return a 404 response."""
        response = self._post(url_kwargs={'user_id': '12345'})
        self.assertEquals(response.status_code, 404)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_bad_project_id(self):
        """Bad project id should cause no change."""
        response = self._post(data={'project_1': '12345'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_add_again(self):
        """Adding project again should have no effect."""
        rel_data = {'project': self.project, 'user': self.user}
        rel = self.create_project_relationship(data=rel_data)

        response = self._post(data=self._data())
        self.assertEquals(response.status_code, 302)
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)

    def test_redirect_to_person_page(self):
        """Adding a relationship should redirect to person page by default."""
        person_url = reverse('view_person', kwargs={'person_id': self.user.pk})

        response = self._post(data=self._data())
        self._assertRedirectsNoFollow(response, person_url)
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)

    def test_redirect_to_next(self):
        """Adding a relationship should redirect to next url if available."""
        response = self._post(data=self._data(), get_kwargs={'next': '/hello'})
        self._assertRedirectsNoFollow(response, '/hello')
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)


class AddUserToProjectTestCase(RelationshipTestBase):
    url_name = 'add_user_to_project'
    perm_name = 'add_projectrelationship'

    def _url_kwargs(self):
        return {'project_id': self.project.pk}

    def _data(self):
        return {'user_1': self.user.pk}

    def test_other_methods(self):
        """Add Project Relationship requires POST."""
        url = reverse(self.url_name, kwargs=self._url_kwargs())
        for method in (self.client.get, self.client.head, self.client.options,
                self.client.put, self.client.delete):
            response = method(url)
            self.assertEquals(response.status_code, 405)
            self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_permission(self):
        """Permission is required to add a project relationship."""
        self.user.user_permissions.remove(self.permission)

        response = self._post()
        self.assertEquals(response.status_code, 302)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_bad_project_id(self):
        """Bad project id should return a 404 response."""
        response = self._post(url_kwargs={'project_id': '12345'})
        self.assertEquals(response.status_code, 404)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_bad_user_id(self):
        """Bad user id should cause no change."""
        response = self._post(data={'user_1': '12345'})
        self.assertEquals(response.status_code, 302)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_add_again(self):
        """Adding user again should have no effect."""
        rel_data = {'project': self.project, 'user': self.user}
        rel = self.create_project_relationship(data=rel_data)

        response = self._post(data=self._data())
        self.assertEquals(response.status_code, 302)
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)

    def test_redirect_to_project_page(self):
        """Adding a relationship hould redirect to person page by default."""
        kwargs = {'project_id': self.project.pk}
        project_url = reverse('view_project', kwargs=kwargs)

        response = self._post(data=self._data())
        self._assertRedirectsNoFollow(response, project_url)
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)

    def test_redirect_to_next(self):
        """Adding a relationship should redirect to next url if available."""
        response = self._post(data=self._data(), get_kwargs={'next': '/hello'})
        self._assertRedirectsNoFollow(response, '/hello')
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)


class EditProjectRelationshipTestCase(RelationshipTestBase):
    url_name = 'edit_project_relationship'
    perm_name = 'change_projectrelationship'

    def _url_kwargs(self):
        return {'project_id': self.project.pk, 'user_id': self.user.pk}

    def _data(self):
        return {'types': [self.rel_type1.pk, self.rel_type2.pk]}

    def setUp(self):
        super(EditProjectRelationshipTestCase, self).setUp()
        rel_data = {'project': self.project, 'user': self.user}
        self.relationship = self.create_project_relationship(data=rel_data)
        self.rel_type1 = self.create_relationship_type()
        self.rel_type2 = self.create_relationship_type()

    def test_permission(self):
        """Permission is required to edit a project relationship."""
        self.user.user_permissions.remove(self.permission)

        for method in (self._get, self._post):
            response = method()
            self.assertEquals(response.status_code, 302)

    def test_bad_user_id(self):
        """Bad user id should return a 404 response."""
        url_kwargs = {'user_id': '12345', 'project_id': self.project.pk}

        for method in (self._get, self._post):
            response = method(url_kwargs=url_kwargs)
            self.assertEquals(response.status_code, 404)
            rel = ProjectRelationship.objects.get()
            self.assertEquals(rel, self.relationship)

    def test_bad_project_id(self):
        """Bad project id should return a 404 response."""
        url_kwargs = {'user_id': self.user.pk, 'project_id': '12345'}

        for method in (self._get, self._post):
            response = method(url_kwargs=url_kwargs)
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
        form = context['relationship_form']
        self.assertEquals(ProjectRelationship.objects.get(), self.relationship)
        self.assertEqual(context['user'], self.user)
        self.assertEqual(context['project'], self.project)
        self.assertFalse(form.is_bound)
        self.assertEquals(form.instance, self.relationship)

    def test_redirect_to_project_page(self):
        """Editing a relationship should redirect to project by default."""
        kwargs = {'project_id': self.project.pk}
        project_url = reverse('view_project', kwargs=kwargs)

        response = self._post(data=self._data())
        self._assertRedirectsNoFollow(response, project_url)
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)
        self.assertEquals(rel.types.count(), 2)
        self.assertTrue(self.rel_type1 in rel.types.all())
        self.assertTrue(self.rel_type2 in rel.types.all())

    def test_redirect_to_next(self):
        """Editing a relationship should redirect to next url if available."""
        response = self._post(data=self._data(), get_kwargs={'next': '/hello'})
        self._assertRedirectsNoFollow(response, '/hello')
        rel = ProjectRelationship.objects.get()
        self.assertEquals(rel.project, self.project)
        self.assertEquals(rel.user, self.user)
        self.assertEquals(rel.types.count(), 2)
        self.assertTrue(self.rel_type1 in rel.types.all())
        self.assertTrue(self.rel_type2 in rel.types.all())


class RemoveProjectRelationshipTestCase(RelationshipTestBase):
    url_name = 'remove_project_relationship'
    perm_name = 'delete_projectrelationship'

    def setUp(self):
        super(RemoveProjectRelationshipTestCase, self).setUp()
        rel_data = {'project': self.project, 'user': self.user}
        self.relationship = self.create_project_relationship(data=rel_data)

    def _url_kwargs(self):
        return {'project_id': self.project.pk, 'user_id': self.user.pk}

    def test_other_methods(self):
        """Remove Project Relationship requires POST."""
        url = reverse(self.url_name, kwargs=self._url_kwargs())
        for method in (self.client.get, self.client.head, self.client.options,
                self.client.put, self.client.delete):
            response = method(url)
            self.assertEquals(response.status_code, 405)
            self.assertEquals(ProjectRelationship.objects.count(), 1)

    def test_permission(self):
        """Permission is required to delete a project relationship."""
        self.user.user_permissions.remove(self.permission)

        response = self._post()
        self.assertEquals(response.status_code, 302)
        self.assertEquals(ProjectRelationship.objects.count(), 1)

    def test_bad_user_id(self):
        """Bad user id should return a 404 response."""
        url_kwargs = {'user_id': '12345', 'project_id': self.project.pk}
        response = self._post(url_kwargs=url_kwargs)
        self.assertEquals(response.status_code, 404)
        self.assertEquals(ProjectRelationship.objects.count(), 1)

    def test_bad_project_id(self):
        """Bad project id should return a 404 response."""
        url_kwargs = {'user_id': self.user.pk, 'project_id': '12345'}
        response = self._post(url_kwargs=url_kwargs)
        self.assertEquals(response.status_code, 404)
        self.assertEquals(ProjectRelationship.objects.count(), 1)

    def test_non_existant_relationship(self):
        """Should have no effect."""
        self.relationship.delete()

        response = self._post()
        self.assertEquals(response.status_code, 302)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_redirect_to_project_page(self):
        kwargs = {'project_id': self.project.pk}
        project_url = reverse('view_project', kwargs=kwargs)

        response = self._post()
        self._assertRedirectsNoFollow(response, project_url)
        self.assertEquals(ProjectRelationship.objects.count(), 0)

    def test_redirect_to_next(self):
        response = self._post(get_kwargs={'next': '/hello'})
        self._assertRedirectsNoFollow(response, '/hello')
        self.assertEquals(ProjectRelationship.objects.count(), 0)
