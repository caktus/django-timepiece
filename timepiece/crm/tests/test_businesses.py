from django.contrib.auth.models import Permission
from django.core.urlresolvers import reverse
from django.test import TestCase

from timepiece.tests import factories
from timepiece.tests.base import ViewTestMixin

from ..models import Business


class TestCreateBusinessView(ViewTestMixin, TestCase):
    url_name = 'create_business'
    template_name = 'timepiece/business/create_edit.html'

    def setUp(self):
        self.permissions = [Permission.objects.get(codename='add_business')]
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)

        self.post_data = {
            'name': 'Business',
            'email': 'email@email.com',
            'description': 'Described',
            'notes': 'Notes',
        }

    def test_get_no_permission(self):
        """Permission is required to create a business."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)
        self.assertEquals(Business.objects.count(), 0)

    def test_post_no_permission(self):
        """Permission is required to create a business."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertRedirectsToLogin(response)
        self.assertEquals(Business.objects.count(), 0)

    def test_get(self):
        """GET should return the page with an unbound form."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)

    def test_post_valid(self):
        """POST should create a new business."""
        response = self._post()
        self.assertEquals(Business.objects.count(), 1)
        business = Business.objects.get()
        self.assertRedirectsNoFollow(response, business.get_absolute_url())
        self.assertEquals(business.name, self.post_data['name'])
        self.assertEquals(business.email, self.post_data['email'])
        self.assertEquals(business.description, self.post_data['description'])
        self.assertEquals(business.notes, self.post_data['notes'])

    def test_post_invalid(self):
        """Invalid POST should not create a new business."""
        self.post_data['name'] = ''
        response = self._post()
        self.assertEquals(Business.objects.count(), 0)
        self.assertEquals(response.status_code, 200)
        self.assertTrue('form' in response.context)
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())


class TestDeleteBusinessView(ViewTestMixin, TestCase):
    url_name = 'delete_business'
    template_name = 'timepiece/delete_object.html'

    def setUp(self):
        self.permissions = [Permission.objects.get(codename='delete_business')]
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)

        self.obj = factories.Business()

        self.url_kwargs = {'business_id': self.obj.pk}

    def test_get_no_permission(self):
        """Permission is required to delete a business."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)
        self.assertEquals(Business.objects.count(), 1)

    def test_post_no_permission(self):
        """Permission is required to delete a business."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertRedirectsToLogin(response)
        self.assertEquals(Business.objects.count(), 1)

    def test_get(self):
        """GET should return a confirmation page."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object'], self.obj)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(Business.objects.count(), 1)

    def test_post(self):
        """POST should delete the business."""
        response = self._post()
        self.assertRedirectsNoFollow(response, reverse('list_businesses'))
        self.assertEquals(Business.objects.count(), 0)


class TestEditBusinessView(ViewTestMixin, TestCase):
    url_name = 'edit_business'
    template_name = 'timepiece/business/create_edit.html'


class TestListBusinessesView(ViewTestMixin, TestCase):
    url_name = 'list_businesses'
    template_name = 'timepiece/business/list.html'
    factory = factories.Business
    model = Business

    def setUp(self):
        self.permissions = [Permission.objects.get(codename='view_business')]
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
        obj = self.factory.create(name='hello')
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_multiple_results(self):
        """Page should render if there are multiple search results."""
        obj_list = [self.factory.create(name='hello') for i in range(2)]
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 2)
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
