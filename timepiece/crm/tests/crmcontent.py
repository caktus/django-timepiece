from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission

from timepiece.tests.base import TimepieceDataTestCase

from timepiece.crm.models import Business, Project


class BusinessTest(TimepieceDataTestCase):

    def setUp(self):
        self.user = self.create_user()
        self.login_user(self.user)
        self.url = reverse('create_business')
        self.data = {
            'name': 'Business',
            'email': 'email@email.com',
            'description': 'Described',
            'notes': 'Notes',
        }

    def login_with_permission(self):
        user = self.create_user()
        perm = Permission.objects.get(codename='add_business')
        user.user_permissions.add(perm)
        self.login_user(user)

    def test_user_create_business(self):
        """A regular user shouldnt be able to create a business"""
        response = self.client.get(self.url)
        # They should be redirected to the login page
        self.assertEquals(response.status_code, 302)

        response = self.client.post(self.url, data=self.data)
        self.assertEquals(Business.objects.count(), 0)

    def test_user_create_business_permission(self):
        """A user with permissions should be able to create a business"""
        self.login_with_permission()

        response = self.client.get(self.url)
        self.assertEquals(response.status_code, 200)
        self.assertTemplateUsed(response,
            'timepiece/business/create_edit.html')

        response = self.client.post(self.url, data=self.data)
        self.assertEquals(Business.objects.count(), 1)


class DeleteObjectsTest(TimepieceDataTestCase):
    def setUp(self):
        super(DeleteObjectsTest, self).setUp()
        self.login_with_permission()

    def login_with_permission(self):
        user = self.create_user()
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.login_user(user)

    def test_no_permissions_business(self):
        """Delete urls should not be accessed by regular users"""
        self.login_user(self.user)

        url = reverse('delete_business', args=(self.business.pk,))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

        self.assertEquals(Business.objects.count(), 1)
        response = self.client.post(url, data={'delete': 'delete'})
        self.assertEquals(Business.objects.count(), 1)

    def test_no_permissions_user(self):
        """Delete urls should not be accessed by regular users"""
        self.login_user(self.user)

        user = self.create_user()
        url = reverse('delete_user', args=(user.pk,))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

        self.assertEquals(User.objects.count(), 5)
        response = self.client.post(url, data={'delete': 'delete'})
        self.assertEquals(User.objects.count(), 5)

    def test_no_permissions_project(self):
        """Delete urls should not be accessed by regular users"""
        self.login_user(self.user)

        url = reverse('delete_project', args=(self.project.pk,))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 302)

        self.assertEquals(Project.objects.count(), 2)
        response = self.client.post(url, data={'delete': 'delete'})
        self.assertEquals(Project.objects.count(), 2)

    def test_delete_business(self):
        """A superuser should be able to access the delete page"""
        url = reverse('delete_business', args=(self.business.pk,))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object'], self.business)

        self.assertEquals(Business.objects.count(), 1)
        response = self.client.post(url, data={'delete': 'delete'})
        self.assertEquals(Business.objects.count(), 0)

    def test_delete_user(self):
        """A superuser should be able to access the delete page"""
        user = self.create_user()
        url = reverse('delete_user', args=(user.pk,))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object'], user)

        self.assertEquals(User.objects.count(), 5)
        response = self.client.post(url, data={'delete': 'delete'})
        self.assertEquals(User.objects.count(), 4)

    def test_delete_project(self):
        """A superuser should be able to access the delete page"""
        url = reverse('delete_project', args=(self.project.pk,))

        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['object'], self.project)

        self.assertEquals(Project.objects.count(), 2)
        response = self.client.post(url, data={'delete': 'delete'})
        self.assertEquals(Project.objects.count(), 1)


class ProjectsTest(TimepieceDataTestCase):
    def setUp(self):
        super(ProjectsTest, self).setUp()
        self.login_with_permission()
        self.url = reverse('create_project')

    def login_with_permission(self):
        user = self.create_user()
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self.login_user(user)

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
