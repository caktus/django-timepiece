from django.core.urlresolvers import reverse_lazy
from django.test import TestCase

from timepiece.tests import factories
from timepiece.tests.base import ViewTestMixin

from ..models import Project


class TestCreateProject(ViewTestMixin, TestCase):
    url_name = 'create_project'
    template_name = 'timepiece/project/create_edit.html'
    factory = factories.Project
    model = Project
    permissions = ('crm.add_project',)

    def setUp(self):
        super(TestCreateProject, self).setUp()
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)
        self.post_data = {
            'name': 'Project',
            'business_1': factories.Business().pk,
            'point_person': factories.Superuser().pk,
            'activity_group': factories.ActivityGroup().pk,
            'type': factories.TypeAttribute().pk,
            'status': factories.StatusAttribute().pk,
            'description': 'a project...',
        }

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)
        self.assertEquals(self.model.objects.count(), 0)

    def test_post_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertRedirectsToLogin(response)
        self.assertEquals(self.model.objects.count(), 0)

    def test_get(self):
        """GET should return the page with an unbound form."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('form' in response.context)
        self.assertFalse(response.context['form'].is_bound)
        self.assertEquals(self.model.objects.count(), 0)

    def test_post_valid(self):
        """POST should create a new object and redirect."""
        response = self._post()
        self.assertEquals(self.model.objects.count(), 1)
        obj = self.model.objects.get()
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())
        self.assertEquals(obj.name, self.post_data['name'])
        self.assertEquals(obj.business.pk, self.post_data['business_1'])
        self.assertEquals(obj.point_person.pk, self.post_data['point_person'])
        self.assertEquals(obj.activity_group.pk, self.post_data['activity_group'])
        self.assertEquals(obj.type.pk, self.post_data['type'])
        self.assertEquals(obj.status.pk, self.post_data['status'])
        self.assertEquals(obj.description, self.post_data['description'])

    def test_post_invalid(self):
        """Invalid POST should not create a new object."""
        self.post_data['name'] = ''
        response = self._post()
        self.assertEquals(self.model.objects.count(), 0)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('form' in response.context)
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())


class TestDeleteProject(ViewTestMixin, TestCase):
    url_name = 'delete_project'
    template_name = 'timepiece/delete_object.html'
    model = Project
    factory = factories.Project
    success_url = reverse_lazy('list_projects')
    permissions = ('crm.delete_project',)
    pk_url_kwarg = 'project_id'

    def setUp(self):
        super(TestDeleteProject, self).setUp()
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)
        self.obj = self.factory.create()
        self.url_kwargs = {self.pk_url_kwarg: self.obj.pk}

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)
        self.assertEquals(self.model.objects.count(), 1)

    def test_post_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertRedirectsToLogin(response)
        self.assertEquals(self.model.objects.count(), 1)

    def test_bad_pk(self):
        """View should return 404 response if no object is found."""
        Project.objects.all().delete()
        self.url_kwargs[self.pk_url_kwarg] = 1234
        response = self._get()
        self.assertEquals(response.status_code, 404)

    def test_get(self):
        """GET should return a confirmation page."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('object' in response.context)
        self.assertEquals(response.context['object'], self.obj)
        self.assertEquals(self.model.objects.count(), 1)

    def test_post(self):
        """POST should delete the object."""
        response = self._post()
        self.assertRedirectsNoFollow(response, self.success_url)
        self.assertEquals(self.model.objects.count(), 0)


class TestEditProject(ViewTestMixin, TestCase):
    url_name = 'edit_project'
    template_name = 'timepiece/project/create_edit.html'
    model = Project
    factory = factories.Project
    permissions = ('crm.change_project',)
    pk_url_kwarg = 'project_id'

    def setUp(self):
        super(TestEditProject, self).setUp()
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)
        self.obj = self.factory.create()
        self.url_kwargs = {self.pk_url_kwarg: self.obj.pk}
        self.post_data = {
            'name': 'Project',
            'business_1': factories.Business().pk,
            'point_person': factories.Superuser().pk,
            'activity_group': factories.ActivityGroup().pk,
            'type': factories.TypeAttribute().pk,
            'status': factories.StatusAttribute().pk,
            'description': 'a project...',
        }

    def _assert_no_change(self):
        self.assertEquals(self.model.objects.count(), 1)
        obj = self.model.objects.get()
        self.assertEquals(obj.name, self.obj.name)
        self.assertEquals(obj.business, self.obj.business)
        self.assertEquals(obj.point_person, self.obj.point_person)
        self.assertEquals(obj.activity_group, self.obj.activity_group)
        self.assertEquals(obj.type, self.obj.type)
        self.assertEquals(obj.status, self.obj.status)
        self.assertEquals(obj.description, self.obj.description)

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)
        self._assert_no_change()

    def test_post_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertRedirectsToLogin(response)
        self._assert_no_change()

    def test_bad_pk(self):
        """View should return 404 response if no object is found."""
        Project.objects.all().delete()
        self.url_kwargs[self.pk_url_kwarg] = 1234
        response = self._get()
        self.assertEquals(response.status_code, 404)

    def test_get(self):
        """GET should return the page with an unbound form."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('object' in response.context)
        self.assertEquals(response.context['object'], self.obj)
        self.assertTrue('form' in response.context)
        self.assertFalse(response.context['form'].is_bound)
        self.assertEquals(response.context['form'].instance, self.obj)
        self._assert_no_change()

    def test_post_valid(self):
        """POST should edit the object."""
        response = self._post()
        self.assertEquals(self.model.objects.count(), 1)
        obj = self.model.objects.get()
        self.assertEquals(obj.pk, self.obj.pk)
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())
        self.assertEquals(obj.name, self.post_data['name'])
        self.assertEquals(obj.business.pk, self.post_data['business_1'])
        self.assertEquals(obj.point_person.pk, self.post_data['point_person'])
        self.assertEquals(obj.activity_group.pk, self.post_data['activity_group'])
        self.assertEquals(obj.type.pk, self.post_data['type'])
        self.assertEquals(obj.status.pk, self.post_data['status'])
        self.assertEquals(obj.description, self.post_data['description'])

    def test_post_invalid(self):
        """Invalid POST should not edit the object."""
        self.post_data['name'] = ''
        response = self._post()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('object' in response.context)
        self.assertEquals(response.context['object'], self.obj)
        self.assertTrue('form' in response.context)
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())
        self.assertEquals(response.context['form'].instance, self.obj)
        self._assert_no_change()


class TestListProjects(ViewTestMixin, TestCase):
    url_name = 'list_projects'
    template_name = 'timepiece/project/list.html'
    factory = factories.Project
    model = Project
    permissions = ('crm.view_project',)

    def setUp(self):
        super(TestListProjects, self).setUp()
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)

    def test_list_all(self):
        """If no filters are provided, all objects should be listed."""
        object_list = [self.factory.create() for i in range(3)]
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 3)
        for obj in object_list:
            self.assertTrue(obj in response.context['object_list'])

    def test_list_none(self):
        """Page should render even if there are no objects."""
        self.model.objects.all().delete()
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 0)

    def test_list_one(self):
        """Page should render if there is one object & no search query."""
        obj = self.factory.create()
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 1)
        self.assertEquals(response.context['object_list'].get(), obj)

    def test_no_results(self):
        """Page should render if there are no search results."""
        self.factory.create()
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 0)

    def test_one_result(self):
        """If there is only one search result, user should be redirected."""
        obj = self.factory.create()
        response = self._get(get_kwargs={'status': obj.status.pk})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_multiple_results(self):
        """Page should render if there are multiple search results."""
        obj_list = [self.factory.create(name='hello') for i in range(2)]
        response = self._get(get_kwargs={'search': 'ello'})
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 2)
        for obj in obj_list:
            self.assertTrue(obj in response.context['object_list'])

    def test_filter_name(self):
        """User should be able to filter by search query and status."""
        self.factory.create()
        obj = self.factory.create(name='hello')
        response = self._get(get_kwargs={'search': 'ello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_filter_description(self):
        """User should be able to filter by search query and status."""
        self.factory.create()
        obj = self.factory.create(description='hello')
        response = self._get(get_kwargs={'search': 'ello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_filter_status(self):
        """User should be able to filter by search query and status."""
        self.factory.create()
        obj = self.factory.create()
        response = self._get(get_kwargs={'status': obj.status.pk})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_filter_query_and_status(self):
        """User should be able to filter by search query and status."""
        obj = self.factory.create(name='hello')
        self.factory.create(status=obj.status)
        self.factory.create(description='hello')
        get_kwargs = {'status': obj.status.pk, 'search': 'ello'}
        response = self._get(get_kwargs=get_kwargs)
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())


class TestViewProject(ViewTestMixin, TestCase):
    url_name = 'view_project'
    template_name = 'timepiece/project/view.html'
    model = Project
    factory = factories.Project
    permissions = ('crm.view_project',)
    pk_url_kwarg = 'project_id'

    def setUp(self):
        super(TestViewProject, self).setUp()
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)
        self.obj = self.factory.create()
        self.url_kwargs = {self.pk_url_kwarg: self.obj.pk}

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)

    def test_post(self):
        """This is a GET-only view."""
        response = self._post()
        self.assertEquals(response.status_code, 405)

    def test_bad_pk(self):
        """View should return 404 response if no object is found."""
        Project.objects.all().delete()
        self.url_kwargs[self.pk_url_kwarg] = 1234
        response = self._get()
        self.assertEquals(response.status_code, 404)

    def test_get(self):
        """User should be able to view the object detail."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('object' in response.context)
        self.assertEquals(response.context['object'], self.obj)
        self.assertTrue('add_user_form' in response.context)
        self.assertFalse(response.context['add_user_form'].is_bound)
