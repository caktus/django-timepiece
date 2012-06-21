from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission

from timepiece import models as timepiece
from timepiece.tests.base import TimepieceDataTestCase


class BusinessTest(TimepieceDataTestCase):
    def setUp(self):
        self.client.login(username='user', password='abc')
        self.url = reverse('create_business')
        self.data = {
            'name': 'Business',
            'email': 'email@email.com',
            'description': 'Described',
            'notes': 'Notes',
        }

    def login_with_permission(self):
        user = User.objects.create_user('admin', 'e@e.com', 'abc')
        perm = Permission.objects.get(codename='add_business')
        user.user_permissions.add(perm)
        self.client.login(username='admin', password='abc')

    def test_user_create_business(self):
        """A regular user shouldnt be able to create a business"""
        response = self.client.get(self.url)
        # They should be redirected to the login page
        self.assertEquals(response.status_code, 302)

        response = self.client.post(self.url, data=self.data)
        self.assertEquals(timepiece.Business.objects.count(), 0)

    def test_user_create_business_permission(self):
        """A user with permissions should be able to create a business"""
        self.login_with_permission()

        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response,
            'timepiece/business/create_edit.html')

        response = self.client.post(self.url, data=self.data)
        self.assertEquals(timepiece.Business.objects.count(), 1)


class DeleteObjectsTest(TimepieceDataTestCase):
    def setUp(self):
        super(DeleteObjectsTest, self).setUp()
        self.login_with_permission()

    def login_with_permission(self):
        user = User.objects.create_user('admin', 'e@e.com', 'abc')
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.client.login(username='admin', password='abc')

    def test_no_permissions_business(self):
        """Delete urls should not be accessed by regular users"""
        self.client.login(username='user', password='abc')

        url = reverse('delete_business', args=(self.business.pk,))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

        self.assertEquals(timepiece.Business.objects.count(), 1)
        response = self.client.post(url, data={'delete': 'delete'})
        self.assertEquals(timepiece.Business.objects.count(), 1)

    def test_no_permissions_person(self):
        """Delete urls should not be accessed by regular users"""
        self.client.login(username='user', password='abc')

        person = self.create_person()
        url = reverse('delete_person', args=(person.pk,))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

        self.assertEquals(User.objects.count(), 5)
        response = self.client.post(url, data={'delete': 'delete'})
        self.assertEquals(User.objects.count(), 5)

    def test_no_permissions_project(self):
        """Delete urls should not be accessed by regular users"""
        self.client.login(username='user', password='abc')

        url = reverse('delete_project', args=(self.project.pk,))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

        self.assertEquals(timepiece.Project.objects.count(), 2)
        response = self.client.post(url, data={'delete': 'delete'})
        self.assertEquals(timepiece.Project.objects.count(), 2)

    def test_delete_business(self):
        """A superuser should be able to access the delete page"""
        url = reverse('delete_business', args=(self.business.pk,))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object'], self.business)

        self.assertEquals(timepiece.Business.objects.count(), 1)
        response = self.client.post(url, data={'delete': 'delete'})
        self.assertEquals(timepiece.Business.objects.count(), 0)

    def test_delete_person(self):
        """A superuser should be able to access the delete page"""
        person = self.create_person()
        url = reverse('delete_person', args=(person.pk,))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object'], person)

        self.assertEquals(User.objects.count(), 5)
        response = self.client.post(url, data={'delete': 'delete'})
        self.assertEquals(User.objects.count(), 4)

    def test_delete_project(self):
        """A superuser should be able to access the delete page"""
        url = reverse('delete_project', args=(self.project.pk,))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object'], self.project)

        self.assertEquals(timepiece.Project.objects.count(), 2)
        response = self.client.post(url, data={'delete': 'delete'})
        self.assertEquals(timepiece.Project.objects.count(), 1)


class ProjectsTest(TimepieceDataTestCase):
    def setUp(self):
        super(ProjectsTest, self).setUp()
        self.login_with_permission()
        self.url = reverse('create_project')

    def login_with_permission(self):
        user = User.objects.create_user('admin', 'e@e.com', 'abc')
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.client.login(username='admin', password='abc')

    def test_create_project_no_business(self):
        """
        If you try to create a project without a business
        you should see the same page with error form
        """
        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)

        response = self.client.post(self.url)
        form = response.context['form']
        self.assertTrue([f.error_messages for f in form.fields.values()])
