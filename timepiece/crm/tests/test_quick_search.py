from django.test import TestCase

from timepiece.tests import factories
from timepiece.tests.base import ViewTestMixin


class TestQuickSearchView(ViewTestMixin, TestCase):
    url_name = 'quick_search'
    template_name = 'timepiece/quick_search.html'

    def setUp(self):
        super(TestQuickSearchView, self).setUp()
        self.user = factories.User()
        self.login_user(self.user)

    def test_search_user(self):
        user = factories.User()
        response = self._post(data={
            'quick_search_1': 'user-{0}'.format(user.pk),
        })
        self.assertRedirectsNoFollow(response, user.get_absolute_url())

    def test_search_no_such_user(self):
        response = self._post(data={
            'quick_search_1': 'user-12345',
        })
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(self.template_name)
        self.assertFalse(response.context['form'].is_valid())

    def test_search_business(self):
        business = factories.Business()
        response = self._post(data={
            'quick_search_1': 'business-{0}'.format(business.pk),
        })
        self.assertRedirectsNoFollow(response, business.get_absolute_url())

    def test_search_no_such_business(self):
        response = self._post(data={
            'quick_search_1': 'business-12345',
        })
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(self.template_name)
        self.assertFalse(response.context['form'].is_valid())

    def test_search_project(self):
        project = factories.Project()
        response = self._post(data={
            'quick_search_1': 'project-{0}'.format(project.pk),
        })
        self.assertRedirectsNoFollow(response, project.get_absolute_url())

    def test_search_no_such_project(self):
        response = self._post(data={
            'quick_search_1': 'project-12345',
        })
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFalse(response.context['form'].is_valid())

    def test_malformed_search(self):
        response = self._post(data={
            'quick_search_1': 'project no dash 12345',
        })
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFalse(response.context['form'].is_valid())

    def test_bad_result_type(self):
        response = self._post(data={
            'quick_search_1': 'hello-12345',
        })
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFalse(response.context['form'].is_valid())

    def test_no_search(self):
        response = self._post(data={
            'quick_search_1': '',
        })
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertFalse(response.context['form'].is_valid())
