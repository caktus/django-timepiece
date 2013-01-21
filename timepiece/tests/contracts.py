from django.contrib.auth.models import Permission

from timepiece.models import ProjectContract
from timepiece.tests.base import TimepieceDataTestCase


class ContractListTestCase(TimepieceDataTestCase):
    url_name = 'list_contracts'
    perm_names = [('timepiece', 'add_projectcontract')]

    def setUp(self):
        get_perm = lambda ct, n: Permission.objects.get(
                content_type__app_label=ct, codename=n)
        self.permissions = [get_perm(*perm) for perm in self.perm_names]

        self.username = self.random_string(25)
        self.password = self.random_string(25)
        self.email = self.random_string(25) + '@example.com'
        self.user = self.create_user(self.username, self.email, self.password)
        self.user.user_permissions.add(*self.permissions)
        self.client.login(username=self.username, password=self.password)

        self.project1 = self.create_project()
        self.project2 = self.create_project()
        self.projects = [self.project1, self.project2]

    def test_permission(self):
        """Permission is required to see this view."""
        response = self._get()
        self.assertEqual(response.status_code, 200)

    def test_no_permission(self):
        """Permission is required to see this view."""
        self.user.user_permissions.remove(*self.permissions)
        response = self._get()
        self.assertEqual(response.status_code, 302)

    def test_no_contracts(self):
        """List should return all current contracts."""
        ProjectContract.objects.all().delete()
        response = self._get()
        self.assertEqual(response.status_code, 200)
        contracts = response.context['contracts']
        self.assertEqual(len(contracts), 0)

    def test_one_contract(self):
        """List should return all current contracts."""
        correct_contract = self.create_contract(projects=self.projects,
                status='current')
        response = self._get()
        self.assertEqual(response.status_code, 200)
        contracts = response.context['contracts']
        self.assertEqual(len(contracts), 1)
        self.assertTrue(correct_contract in contracts)

    def test_contracts(self):
        """List should return all current contracts."""
        correct_contracts = [self.create_contract(projects=self.projects,
                status='current') for i in range(3)]
        response = self._get()
        self.assertEqual(response.status_code, 200)
        contracts = response.context['contracts']
        self.assertEqual(len(contracts), 3)
        for i in range(3):
            self.assertTrue(correct_contracts[i] in contracts)

    def test_non_current_contracts(self):
        """List should return all current contracts."""
        complete_contract = self.create_contract(projects=self.projects,
                status='complete')
        upcoming_contract = self.create_contract(projects=self.projects,
                status='upcoming')
        response = self._get()
        self.assertEqual(response.status_code, 200)
        contracts = response.context['contracts']
        self.assertEqual(len(contracts), 0)


class ContractViewTestCase(TimepieceDataTestCase):
    url_name = 'view_contract'
    perm_names = [('timepiece', 'add_projectcontract')]

    @property
    def url_args(self):
        return (self.contract.pk,)

    def setUp(self):
        get_perm = lambda ct, n: Permission.objects.get(
                content_type__app_label=ct, codename=n)
        self.permissions = [get_perm(*perm) for perm in self.perm_names]

        self.username = self.random_string(25)
        self.password = self.random_string(25)
        self.email = self.random_string(25) + '@example.com'
        self.user = self.create_user(self.username, self.email, self.password)
        self.user.user_permissions.add(*self.permissions)
        self.client.login(username=self.username, password=self.password)

        self.project1 = self.create_project()
        self.project2 = self.create_project()
        self.projects = [self.project1, self.project2]

        self.contract = self.create_contract(projects=self.projects)

    def test_permission(self):
        """Permission is required to view a contract."""
        response = self._get()
        self.assertEqual(response.status_code, 200)

    def test_no_permission(self):
        """Permission is required to view a contract."""
        self.user.user_permissions.remove(*self.permissions)
        response = self._get()
        self.assertEqual(response.status_code, 302)

    def test_bad_id(self):
        response = self._get(url_args=('12345',))
        self.assertEqual(response.status_code, 404)

    def test_current_contract(self):
        contract = self.create_contract(projects=self.projects,
                status='current')
        response = self._get(url_args=(contract.pk,))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(contract, response.context['contract'])

    def test_upcoming_contract(self):
        contract = self.create_contract(projects=self.projects,
                status='upcoming')
        response = self._get(url_args=(contract.pk,))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(contract, response.context['contract'])

    def test_complete_contract(self):
        contract = self.create_contract(projects=self.projects,
                status='complete')
        response = self._get(url_args=(contract.pk,))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(contract, response.context['contract'])
