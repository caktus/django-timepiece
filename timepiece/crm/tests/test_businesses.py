"""
Most of this module's assertRedirectsToLogin statements have been replaced.
Instead of checking for this, it now simply checks for a 403 status code.
This is from switching from the homebrewed cbv_decorator usage of the
permission_denied decorator to the now-standard PermissionRequiredMixin
"""
from django.contrib.auth.models import Permission
from django.urls import reverse_lazy
from django.test import TestCase

from timepiece.tests import factories
from timepiece.tests.base import ViewTestMixin

from ..models import Business


class TestCreateBusiness(ViewTestMixin, TestCase):
    url_name = 'create_business'
    template_name = 'timepiece/business/create_edit.html'
    factory = factories.Business
    model = Business
    permissions = ('crm.add_business',)

    def setUp(self):
        super(TestCreateBusiness, self).setUp()
        self.user = factories.User()
        self.user.user_permissions.add(Permission.objects.get(codename='add_business'))
        self.login_user(self.user)
        self.post_data = {
            'name': 'Business',
            'email': 'email@email.com',
            'description': 'Described',
            'notes': 'Notes',
        }

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.model.objects.count(), 0)

    def test_post_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.model.objects.count(), 0)

    def test_get(self):
        """GET should return the page with an unbound form."""
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('form' in response.context)
        self.assertFalse(response.context['form'].is_bound)
        self.assertEqual(self.model.objects.count(), 0)

    def test_post_valid(self):
        """POST should create a new object and redirect."""
        response = self._post()
        self.assertEqual(self.model.objects.count(), 1)
        obj = self.model.objects.get()
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())
        self.assertEqual(obj.name, self.post_data['name'])
        self.assertEqual(obj.email, self.post_data['email'])
        self.assertEqual(obj.description, self.post_data['description'])
        self.assertEqual(obj.notes, self.post_data['notes'])

    def test_post_invalid(self):
        """Invalid POST should not create a new object."""
        self.post_data['name'] = ''
        response = self._post()
        self.assertEqual(self.model.objects.count(), 0)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('form' in response.context)
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())


class TestDeleteBusiness(ViewTestMixin, TestCase):
    url_name = 'delete_business'
    template_name = 'timepiece/delete_object.html'
    model = Business
    factory = factories.Business
    success_url = reverse_lazy('list_businesses')
    permissions = ('crm.delete_business',)
    pk_url_kwarg = 'business_id'

    def setUp(self):
        super(TestDeleteBusiness, self).setUp()
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)
        self.obj = self.factory.create()
        self.url_kwargs = {self.pk_url_kwarg: self.obj.pk}

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.model.objects.count(), 1)

    def test_post_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.model.objects.count(), 1)

    def test_bad_pk(self):
        """View should return 404 response if no object is found."""
        Business.objects.all().delete()
        self.url_kwargs[self.pk_url_kwarg] = 1234
        response = self._get()
        self.assertEqual(response.status_code, 404)

    def test_get(self):
        """GET should return a confirmation page."""
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('object' in response.context)
        self.assertEqual(response.context['object'], self.obj)
        self.assertEqual(self.model.objects.count(), 1)

    def test_post(self):
        """POST should delete the object."""
        response = self._post()
        self.assertRedirectsNoFollow(response, self.success_url)
        self.assertEqual(self.model.objects.count(), 0)


class TestEditBusiness(ViewTestMixin, TestCase):
    url_name = 'edit_business'
    template_name = 'timepiece/business/create_edit.html'
    model = Business
    factory = factories.Business
    permissions = ('crm.change_business',)
    pk_url_kwarg = 'business_id'

    def setUp(self):
        super(TestEditBusiness, self).setUp()
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)
        self.obj = self.factory.create()
        self.url_kwargs = {self.pk_url_kwarg: self.obj.pk}
        self.post_data = {
            'name': 'Business',
            'email': 'email@email.com',
            'description': 'Described',
            'notes': 'Notes',
        }

    def _assert_no_change(self):
        self.assertEqual(self.model.objects.count(), 1)
        obj = self.model.objects.get()
        self.assertEqual(obj.name, self.obj.name)
        self.assertEqual(obj.email, self.obj.email)
        self.assertEqual(obj.description, self.obj.description)
        self.assertEqual(obj.notes, self.obj.notes)

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertEqual(response.status_code, 403)
        self._assert_no_change()

    def test_post_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertEqual(response.status_code, 403)
        self._assert_no_change()

    def test_bad_pk(self):
        """View should return 404 response if no object is found."""
        Business.objects.all().delete()
        self.url_kwargs[self.pk_url_kwarg] = 1234
        response = self._get()
        self.assertEqual(response.status_code, 404)

    def test_get(self):
        """GET should return the page with an unbound form."""
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('object' in response.context)
        self.assertEqual(response.context['object'], self.obj)
        self.assertTrue('form' in response.context)
        self.assertFalse(response.context['form'].is_bound)
        self.assertEqual(response.context['form'].instance, self.obj)
        self._assert_no_change()

    def test_post_valid(self):
        """POST should edit the object."""
        response = self._post()
        self.assertEqual(self.model.objects.count(), 1)
        obj = self.model.objects.get()
        self.assertEqual(obj.pk, self.obj.pk)
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())
        self.assertEqual(obj.name, self.post_data['name'])
        self.assertEqual(obj.email, self.post_data['email'])
        self.assertEqual(obj.description, self.post_data['description'])
        self.assertEqual(obj.notes, self.post_data['notes'])

    def test_post_invalid(self):
        """Invalid POST should not edit the object."""
        self.post_data['name'] = ''
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('object' in response.context)
        self.assertEqual(response.context['object'], self.obj)
        self.assertTrue('form' in response.context)
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())
        self.assertEqual(response.context['form'].instance, self.obj)
        self._assert_no_change()


class TestListBusinesses(ViewTestMixin, TestCase):
    url_name = 'list_businesses'
    template_name = 'timepiece/business/list.html'
    factory = factories.Business
    model = Business
    permissions = ('crm.view_business',)

    def setUp(self):
        super(TestListBusinesses, self).setUp()
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertEqual(response.status_code, 403)

    def test_list_all(self):
        """If no filters are provided, all objects should be listed."""
        object_list = [self.factory.create() for i in range(3)]
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(response.context['object_list'].count(), 3)
        for obj in object_list:
            self.assertTrue(obj in response.context['object_list'])

    def test_list_none(self):
        """Page should render even if there are no objects."""
        self.model.objects.all().delete()
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(response.context['object_list'].count(), 0)

    def test_list_one(self):
        """Page should render if there is one object & no search query."""
        obj = self.factory.create()
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(response.context['object_list'].count(), 1)
        self.assertEqual(response.context['object_list'].get(), obj)

    def test_no_results(self):
        """Page should render if there are no search results."""
        self.factory.create()
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(response.context['object_list'].count(), 0)

    def test_one_result(self):
        """If there is only one search result, user should be redirected."""
        obj = self.factory.create(name='hello')
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_multiple_results(self):
        """Page should render if there are multiple search results."""
        obj_list = [self.factory.create(name='hello') for i in range(2)]
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(response.context['object_list'].count(), 2)
        for obj in obj_list:
            self.assertTrue(obj in response.context['object_list'])

    def test_filter_name(self):
        """User should be able to filter by search query."""
        self.factory.create()
        obj = self.factory.create(name='hello')
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_filter_description(self):
        """User should be able to filter by search query."""
        self.factory.create()
        obj = self.factory.create(description='hello')
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())


class TestViewBusiness(ViewTestMixin, TestCase):
    url_name = 'view_business'
    template_name = 'timepiece/business/view.html'
    model = Business
    factory = factories.Business
    permissions = ('crm.view_business',)
    pk_url_kwarg = 'business_id'

    def setUp(self):
        super(TestViewBusiness, self).setUp()
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)
        self.obj = self.factory.create()
        self.url_kwargs = {self.pk_url_kwarg: self.obj.pk}

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertEqual(response.status_code, 403)

    def test_post(self):
        """This is a GET-only view."""
        response = self._post()
        self.assertEqual(response.status_code, 405)

    def test_bad_pk(self):
        """View should return 404 response if no object is found."""
        Business.objects.all().delete()
        self.url_kwargs[self.pk_url_kwarg] = 1234
        response = self._get()
        self.assertEqual(response.status_code, 404)

    def test_get(self):
        """User should be able to view the object detail."""
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('object' in response.context)
        self.assertEqual(response.context['object'], self.obj)
