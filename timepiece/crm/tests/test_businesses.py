from django.contrib.auth.models import Permission

from timepiece.tests import factories
from timepiece.tests.base import ViewTestMixin, TimepieceDataTestCase

from ..models import Business


__all__ = ['TestCreateBusinessView', 'TestDeleteBusinessView']


class TestCreateBusinessView(ViewTestMixin, TimepieceDataTestCase):
    url_name = 'create_business'
    template_name = 'timepiece/business/create_edit.html'

    def setUp(self):
        self.permissions = [Permission.objects.get(codename='add_business')]
        self.user = factories.UserFactory(permissions=self.permissions)
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


class TestDeleteBusinessView(ViewTestMixin, TimepieceDataTestCase):
    url_name = 'delete_business'
    template_name = 'timepiece/delete_object.html'

    def setUp(self):
        self.permissions = [Permission.objects.get(codename='delete_business')]
        self.user = factories.UserFactory(permissions=self.permissions)
        self.login_user(self.user)

        self.obj = factories.BusinessFactory.create()

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
        self.assertEquals(Business.objects.count(), 0)
