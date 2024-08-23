"""
Most of this module's use of assertRedirectsToLogin have been replaced
with an assertEqual for status_code 403. This change is from the switch
from the homebrew class-based application of the permission_required
decorator to the now more standard PermissionRequiredMixin
"""

import mock

from django.contrib.auth.models import User, Permission
from django.urls import reverse, reverse_lazy
from django.test import TestCase

from timepiece.tests import factories
from timepiece.tests.base import ViewTestMixin


class TestAddToUserClass(TestCase):
    """Tests for methods added to the user model via User.add_to_class."""

    def setUp(self):
        super(TestAddToUserClass, self).setUp()
        self.user = factories.User()

    @mock.patch('timepiece.crm.models.get_active_entry')
    def test_clocked_in(self, get_active_entry):
        get_active_entry.return_value = True
        self.assertTrue(self.user.clocked_in)

    @mock.patch('timepiece.crm.models.get_active_entry')
    def test_not_clocked_in(self, get_active_entry):
        get_active_entry.return_value = None
        self.assertFalse(self.user.clocked_in)

    def test_get_name(self):
        self.assertEqual(self.user.get_name_or_username(), self.user.get_full_name())

    def test_get_username(self):
        self.user.first_name = ""
        self.user.last_name = ""
        self.assertEqual(self.user.get_name_or_username(), self.user.username)

    def test_get_absolute_url(self):
        correct = reverse('view_user', args=(self.user.pk,))
        self.assertEqual(self.user.get_absolute_url(), correct)


class TestCreateUser(ViewTestMixin, TestCase):
    url_name = 'create_user'
    template_name = 'timepiece/user/create_edit.html'
    factory = factories.User
    model = User
    permissions = ('auth.add_user',)

    def setUp(self):
        super(TestCreateUser, self).setUp()
        self.user = factories.User()
        self.user.user_permissions.add(Permission.objects.get(codename='add_user'))
        self.login_user(self.user)
        self.post_data = {
            'username': 'hello',
            'first_name': 'Sam',
            'last_name': 'Blue',
            'email': 'sam@blue.com',
            'is_active': False,
            'is_staff': True,
            'groups': [factories.Group().pk, factories.Group().pk],
            'password1': 'aaa',
            'password2': 'aaa',
        }

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

    def test_get(self):
        """GET should return the page with an unbound form."""
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('form' in response.context)
        self.assertFalse(response.context['form'].is_bound)
        self.assertEqual(self.model.objects.count(), 1)

    def test_post_valid(self):
        """POST should create a new object and redirect."""
        response = self._post()
        self.assertEqual(self.model.objects.count(), 2)
        obj = self.model.objects.exclude(pk=self.user.pk).get()
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())
        self.assertEqual(obj.username, self.post_data['username'])
        self.assertEqual(obj.first_name, self.post_data['first_name'])
        self.assertEqual(obj.last_name, self.post_data['last_name'])
        self.assertEqual(obj.email, self.post_data['email'])
        self.assertEqual(obj.is_active, self.post_data['is_active']),
        self.assertEqual(obj.is_staff, self.post_data['is_staff']),
        groups = obj.groups.values_list('pk', flat=True)
        self.assertEqual(sorted(groups), sorted(self.post_data['groups']))
        self.assertTrue(obj.check_password(self.post_data['password1']))

    def test_nonmatching_passwords(self):
        """Passwords must match."""
        self.post_data['password2'] = 'bbb'
        response = self._post()
        self.assertEqual(self.model.objects.count(), 1)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('form' in response.context)
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())

    def test_post_invalid(self):
        """Invalid POST should not create a new object."""
        self.post_data['username'] = ''
        response = self._post()
        self.assertEqual(self.model.objects.count(), 1)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('form' in response.context)
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())


class TestDeleteUser(ViewTestMixin, TestCase):
    url_name = 'delete_user'
    template_name = 'timepiece/delete_object.html'
    model = User
    factory = factories.User
    success_url = reverse_lazy('list_users')
    permissions = ('auth.delete_user',)
    pk_url_kwarg = 'user_id'

    def setUp(self):
        super(TestDeleteUser, self).setUp()
        self.user = factories.User()
        self.user.user_permissions.add(Permission.objects.get(codename='delete_user'))
        self.login_user(self.user)
        self.obj = self.factory.create()
        self.url_kwargs = {self.pk_url_kwarg: self.obj.pk}

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.model.objects.count(), 2)

    def test_post_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._post()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), 2)

    def test_bad_pk(self):
        """View should return 404 response if no object is found."""
        User.objects.exclude(id=self.user.id).delete()
        self.url_kwargs[self.pk_url_kwarg] = 1234
        response = self._get()
        self.assertEqual(response.status_code, 404)

    def test_get(self):
        """GET should returd return a confirmation page."""
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('object' in response.context)
        self.assertEqual(response.context['object'], self.obj)
        self.assertEqual(self.model.objects.count(), 2)

    def test_post(self):
        """POST should delete the object."""
        response = self._post()
        self.assertRedirectsNoFollow(response, self.success_url)
        self.assertEqual(User.objects.count(), 1)


class TestEditUser(ViewTestMixin, TestCase):
    url_name = 'edit_user'
    template_name = 'timepiece/user/create_edit.html'
    permissions = ('auth.change_user',)
    model = User
    factory = factories.User
    pk_url_kwarg = 'user_id'

    def setUp(self):
        super(TestEditUser, self).setUp()
        self.user = factories.User()
        self.user.user_permissions.add(Permission.objects.get(codename='change_user'))
        self.login_user(self.user)
        self.obj = self.factory.create()
        self.url_kwargs = {self.pk_url_kwarg: self.obj.pk}
        self.post_data = {
            'username': 'hello',
            'first_name': 'Sam',
            'last_name': 'Blue',
            'email': 'sam@blue.com',
            'is_active': False,
            'is_staff': True,
            'groups': [factories.Group().pk, factories.Group().pk],
        }

    def _assert_no_change(self):
        self.assertEqual(self.model.objects.count(), 2)
        obj = self.model.objects.get(pk=self.obj.pk)
        self.assertEqual(obj.username, self.obj.username)
        self.assertEqual(obj.first_name, self.obj.first_name)
        self.assertEqual(obj.last_name, self.obj.last_name)
        self.assertEqual(obj.email, self.obj.email)
        self.assertEqual(obj.is_active, self.obj.is_active)
        self.assertEqual(obj.is_staff, self.obj.is_staff)
        groups1 = obj.groups.values_list('pk', flat=True)
        groups2 = self.obj.groups.values_list('pk', flat=True)
        self.assertEqual(sorted(groups1), sorted(groups2))

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
        User.objects.exclude(id=self.user.id).delete()
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
        self.assertEqual(self.model.objects.count(), 2)
        obj = self.model.objects.get(pk=self.obj.pk)
        self.assertEqual(obj.pk, self.obj.pk)
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())
        self.assertEqual(obj.first_name, self.post_data['first_name'])
        self.assertEqual(obj.last_name, self.post_data['last_name'])
        self.assertEqual(obj.email, self.post_data['email'])
        self.assertEqual(obj.is_active, self.post_data['is_active'])
        self.assertEqual(obj.is_staff, self.post_data['is_staff'])
        groups = obj.groups.values_list('pk', flat=True)
        self.assertEqual(sorted(groups), sorted(self.post_data['groups']))

    def test_post_invalid(self):
        """Invalid POST should not edit the object."""
        self.post_data['username'] = ''
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('object' in response.context)
        self.assertEqual(response.context['object'], self.obj)
        self.assertTrue('form' in response.context)
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())
        self._assert_no_change()

    def test_matching_passwords(self):
        """Matching passwords are required to change the password."""
        self.post_data['password1'] = 'aaa'
        self.post_data['password2'] = 'aaa'
        response = self._post()
        self.assertRedirectsNoFollow(response, self.obj.get_absolute_url())
        obj = self.model.objects.get(pk=self.obj.pk)
        self.assertTrue(obj.check_password('aaa'))

    def test_nonmatching_passwords(self):
        """Object shouldn't be edited if passwords are given but unmatching."""
        self.post_data['password1'] = 'aaa'
        self.post_data['password2'] = 'bbb'
        response = self._post()
        self.assertEqual(response.status_code, 200)
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
        self.assertEqual(updated_user.groups.count(), 2)
        self.assertTrue(groups[0] in updated_user.groups.all())
        self.assertTrue(groups[1] in updated_user.groups.all())


class TestListUsers(ViewTestMixin, TestCase):
    url_name = 'list_users'
    template_name = 'timepiece/user/list.html'
    factory = factories.User
    model = User

    def setUp(self):
        super(TestListUsers, self).setUp()
        # This permission is not created by Django by default.
        self.user = factories.User()
        self.user.user_permissions.add(Permission.objects.get(codename='view_user'))
        self.login_user(self.user)

    def test_get_no_permission(self):
        """Permission is required for this view."""
        self.user.user_permissions.clear()
        response = self._get()
        self.assertEqual(response.status_code, 403)

    def test_list_all(self):
        """If no filters are provided, all objects should be listed."""
        object_list = [self.factory.create() for i in range(2)] + [self.user]
        response = self._get()
        # Gets an HttpResponseRedirect, a 302 status code
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(response.context['object_list'].count(), 3)
        for obj in object_list:
            self.assertTrue(obj in response.context['object_list'])

    def test_list_one(self):
        """Page should render if there is one object & no search query."""
        response = self._get()
        # Gets an HttpResponseRedirct, a 302 status code
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(response.context['object_list'].count(), 1)
        self.assertEqual(response.context['object_list'].get(), self.user)

    def test_no_results(self):
        """Page should render if there are no search results."""
        self.factory.create()
        response = self._get(get_kwargs={'search': 'hello'})
        # The above call returns an HttpResponseRedirect, yielding a 302 status code
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(response.context['object_list'].count(), 0)

    def test_one_result(self):
        """If there is only one search result, user should be redirected."""
        obj = self.factory.create(first_name='hello')
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_multiple_results(self):
        """Page should render if there are multiple search results."""
        obj_list = [self.factory.create(first_name='hello') for i in range(2)]
        response = self._get(get_kwargs={'search': 'hello'})
        # The above response is an HttpResponseRedirect, yielding a 302
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertEqual(response.context['object_list'].count(), 2)
        for obj in obj_list:
            self.assertTrue(obj in response.context['object_list'])

    def test_filter_first_name(self):
        """User should be able to filter by search query."""
        self.factory.create()
        obj = self.factory.create(first_name='hello')
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_filter_last_name(self):
        """User should be able to filter by search query."""
        self.factory.create()
        obj = self.factory.create(last_name='hello')
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_filter_email(self):
        """User should be able to filter by search query."""
        self.factory.create()
        obj = self.factory.create(email='hello@example.com')
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())

    def test_filter_username(self):
        """User should be able to filter by search query."""
        self.factory.create()
        obj = self.factory.create(username='hello')
        response = self._get(get_kwargs={'search': 'hello'})
        self.assertRedirectsNoFollow(response, obj.get_absolute_url())


class TestViewUser(ViewTestMixin, TestCase):
    url_name = 'view_user'
    template_name = 'timepiece/user/view.html'
    model = User
    factory = factories.User
    permissions = ('auth.view_user')
    pk_url_kwarg = 'user_id'
    login_url = reverse('auth_login')

    def setUp(self):
        super(TestViewUser, self).setUp()
        self.user = factories.User()
        self.user.user_permissions.add(Permission.objects.get(codename='view_user'))
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
        User.objects.exclude(id=self.user.id).delete()
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


class TestEditSettings(ViewTestMixin, TestCase):
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

    def test_unauthenticated(self):
        """User must be logged in for this view."""
        self.client.logout()
        response = self._get()
        self.assertRedirectsToLogin(response)

    def test_get(self):
        """GET should return the page with an unbound form."""
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFalse(response.context['form'].is_bound)

    def test_post_valid(self):
        """POST should edit the authenticated user's data."""
        response = self._post()
        self.assertRedirectsNoFollow(response, reverse('dashboard'))
        updated_user = User.objects.get(pk=self.user.pk)
        for k, v in self.post_data.items():
            self.assertEqual(getattr(updated_user, k), v)

    def test_post_invalid(self):
        """Invalid POST should not edit data."""
        self.post_data['email'] = ''
        response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertTrue('form' in response.context)
        self.assertTrue(response.context['form'].is_bound)
        self.assertFalse(response.context['form'].is_valid())
        obj = User.objects.get(pk=self.user.pk)
        self.assertEqual(obj.first_name, self.user.first_name)
        self.assertEqual(obj.last_name, self.user.last_name)
        self.assertEqual(obj.email, self.user.email)

    def test_redirect_to_next(self):
        """Passing next parameter should customize the redirect location."""
        response = self._post(get_kwargs={'next': '/hello/'})
        self.assertRedirectsNoFollow(response, '/hello/')
        updated_user = User.objects.get(pk=self.user.pk)
        for k, v in self.post_data.items():
            self.assertEqual(getattr(updated_user, k), v)
