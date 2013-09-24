from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.test import TestCase

from timepiece.tests import factories
from timepiece.tests.base import ViewTestMixin


__all__ = ['TestDeleteUserView', 'TestEditUserView', 'TestListUsersView',
        'TestEditSettingsView']


class TestDeleteUserView(ViewTestMixin, TestCase):
    url_name = 'delete_user'
    template_name = 'timepiece/delete_object.html'

    def setUp(self):
        self.permissions = [Permission.objects.get(codename='delete_user')]
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)

        self.obj = factories.User()

        self.url_kwargs = {'user_id': self.obj.pk}

    def test_get_no_permission(self):
        """Permission is required to delete a user."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)
        self.assertEquals(User.objects.count(), 2)

    def test_post_no_permission(self):
        """Permission is required to delete a user."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertRedirectsToLogin(response)
        self.assertEquals(User.objects.count(), 2)

    def test_get(self):
        """GET should return a confirmation page."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object'], self.obj)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(User.objects.count(), 2)

    def test_post(self):
        """POST should delete the user."""
        response = self._post()
        self.assertEquals(User.objects.count(), 1)


class TestEditUserView(ViewTestMixin, TestCase):
    url_name = 'edit_user'
    template_name = 'timepiece/user/create_edit.html'

    def setUp(self):
        self.permissions = [Permission.objects.get(codename='change_user')]
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)

        self.obj = factories.User()
        self.url_kwargs = {'user_id': self.obj.pk}

        self.post_data = {
            'username': self.obj.username,
            'first_name': self.obj.first_name,
            'last_name': self.obj.last_name,
            'email': self.obj.email,
            'is_active': self.obj.is_active,
            'is_staff': self.obj.is_staff,
            'groups': self.obj.groups.values_list('pk', flat=True),
        }

    def test_get_no_permission(self):
        """Permission is required to edit a user."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)

    def test_post_no_permission(self):
        """Permission is required to edit a user."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertRedirectsToLogin(response)

    def test_get(self):
        """GET should return the page with an unbound form."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFalse(response.context['form'].is_bound)

    def test_post_valid(self):
        """POST should edit the existing user."""
        self.post_data['first_name'] = 'hello'
        response = self._post()
        self.assertRedirectsNoFollow(response, self.obj.get_absolute_url())
        updated_user = User.objects.get(pk=self.obj.pk)
        self.assertEquals(updated_user.first_name, self.post_data['first_name'])

    def test_matching_passwords(self):
        """Matching passwords are required."""
        self.post_data['password_one'] = 'aaa'
        self.post_data['password_two'] = 'bbb'
        response = self._post()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        form = response.context['form']
        self.assertTrue(form.is_bound)
        self.assertFalse(form.is_valid())

    def test_edit_groups(self):
        """Should be able to update user's auth groups."""
        groups = [factories.Group() for i in range(2)]
        self.post_data['groups'] = [g.pk for g in groups]
        response = self._post()
        self.assertRedirectsNoFollow(response, self.obj.get_absolute_url())
        updated_user = User.objects.get(pk=self.obj.pk)
        self.assertEquals(updated_user.groups.count(), 2)
        self.assertTrue(groups[0] in updated_user.groups.all())
        self.assertTrue(groups[1] in updated_user.groups.all())


class TestListUsersView(ViewTestMixin, TestCase):
    url_name = 'list_users'
    template_name = 'timepiece/user/list.html'
    factory = factories.User
    model = User

    def setUp(self):
        ct = ContentType.objects.get(model='user')
        p = Permission.objects.create(content_type=ct, codename='view_user')
        self.permissions = [p]
        self.user = factories.User(permissions=self.permissions)
        self.login_user(self.user)

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertRedirectsToLogin(response)

    def test_list_all(self):
        """If no filters are provided, all objects should be listed."""
        object_list = [self.factory.create() for i in range(2)] + [self.user]
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 3)
        for obj in object_list:
            self.assertTrue(obj in response.context['object_list'])

    def test_list_one(self):
        """Page should render if there is one object & no search query."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 1)
        self.assertEquals(response.context['object_list'].get(), self.user)

    def test_no_results(self):
        """Page should render if there are no search results."""
        obj = self.factory.create()
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 0)

    def test_one_result(self):
        """If there is only one search result, user should be redirected."""
        obj = self.factory.create(first_name='hello')
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_multiple_results(self):
        """Page should render if there are multiple search results."""
        obj_list = [self.factory.create(first_name='hello') for i in range(2)]
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEquals(response.context['object_list'].count(), 2)
        for obj in obj_list:
            self.assertTrue(obj in response.context['object_list'])

    def test_filter_first_name(self):
        """User should be able to filter by search query."""
        obj = self.factory.create(first_name='hello')
        other_obj = self.factory.create()
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_filter_last_name(self):
        """User should be able to filter by search query."""
        obj = self.factory.create(last_name='hello')
        other_obj = self.factory.create()
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_filter_email(self):
        """User should be able to filter by search query."""
        obj = self.factory.create(email='hello@example.com')
        other_obj = self.factory.create()
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_filter_username(self):
        """User should be able to filter by search query."""
        obj = self.factory.create(username='hello')
        other_obj = self.factory.create()
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())


class TestEditSettingsView(ViewTestMixin, TestCase):
    url_name = 'edit_settings'
    template_name = 'timepiece/user/settings.html'

    def setUp(self):
        self.user = factories.User()
        self.login_user(self.user)

        self.post_data = {
            'first_name': 'First',
            'last_name': 'Last',
            'email': 'hello@example.com',
        }

    def test_get(self):
        """GET should return the page with an unbound form."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFalse(response.context['form'].is_bound)

    def test_post_valid(self):
        response = self._post()
        self.assertRedirectsNoFollow(response, reverse('dashboard'))
        updated_user = User.objects.get(pk=self.user.pk)
        for k, v in self.post_data.iteritems():
            self.assertEquals(getattr(updated_user, k), v)

    def test_redirect_to_next(self):
        response = self._post(get_kwargs={'next': '/hello/'})
        self.assertRedirectsNoFollow(response, '/hello/')

        updated_user = User.objects.get(pk=self.user.pk)
        for k, v in self.post_data.iteritems():
            self.assertEquals(getattr(updated_user, k), v)
