import datetime
import mock

from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError

from timepiece.contracts.models import ProjectContract, ContractHour
from timepiece.tests.base import TimepieceDataTestCase, ViewTestMixin


class ContractListTestCase(ViewTestMixin, TimepieceDataTestCase):
    url_name = 'list_contracts'
    perm_names = [('contracts', 'add_projectcontract')]

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
                status=ProjectContract.STATUS_CURRENT)
        response = self._get()
        self.assertEqual(response.status_code, 200)
        contracts = response.context['contracts']
        self.assertEqual(len(contracts), 1)
        self.assertTrue(correct_contract in contracts)

    def test_contracts(self):
        """List should return all current contracts."""
        correct_contracts = [self.create_contract(projects=self.projects,
                status=ProjectContract.STATUS_CURRENT) for i in range(3)]
        response = self._get()
        self.assertEqual(response.status_code, 200)
        contracts = response.context['contracts']
        self.assertEqual(len(contracts), 3)
        for i in range(3):
            self.assertTrue(correct_contracts[i] in contracts)

    def test_non_current_contracts(self):
        """List should return all current contracts."""
        complete_contract = self.create_contract(projects=self.projects,
                status=ProjectContract.STATUS_COMPLETE)
        upcoming_contract = self.create_contract(projects=self.projects,
                status=ProjectContract.STATUS_UPCOMING)
        response = self._get()
        self.assertEqual(response.status_code, 200)
        contracts = response.context['contracts']
        self.assertEqual(len(contracts), 0)


class ContractViewTestCase(ViewTestMixin, TimepieceDataTestCase):
    url_name = 'view_contract'
    perm_names = [('contracts', 'add_projectcontract')]

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
                status=ProjectContract.STATUS_CURRENT)
        response = self._get(url_args=(contract.pk,))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(contract, response.context['contract'])

    def test_upcoming_contract(self):
        contract = self.create_contract(projects=self.projects,
                status=ProjectContract.STATUS_UPCOMING)
        response = self._get(url_args=(contract.pk,))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(contract, response.context['contract'])

    def test_complete_contract(self):
        contract = self.create_contract(projects=self.projects,
                status=ProjectContract.STATUS_COMPLETE)
        response = self._get(url_args=(contract.pk,))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(contract, response.context['contract'])


class ContractHourTestCase(TimepieceDataTestCase):

    def test_defaults(self):
        contract_hour = ContractHour()
        self.assertEqual(0, contract_hour.hours)
        self.assertEqual(ContractHour.PENDING_STATUS, contract_hour.status)

    def test_contracted_hours(self):
        # If we create some Contract Hour objects and then go to the
        # project contract and get contracted_hours(), it gives the sum
        # of the hours
        pc = self.create_contract(num_hours=4)
        self.assertEqual(4, pc.contracted_hours())
        self.assertEqual(0, pc.pending_hours())

    def test_pending_hours(self):
        # If we create some pending Contract Hour objects and then go to the
        # project contract and get pending_hours(), it gives the sum
        # of the hours
        pc = self.create_contract(num_hours=4)
        ch = self.create_contract_hour({
            'contract': pc,
            'hours': 27,
            'status': ContractHour.PENDING_STATUS
        })
        self.assertEqual(4, pc.contracted_hours())
        self.assertEqual(27, pc.pending_hours())
        ch.delete()
        self.assertEqual(4, pc.contracted_hours())
        self.assertEqual(0, pc.pending_hours())

    def test_validation(self):
        with self.assertRaises(ValidationError):
            ch = self.create_contract_hour({
                'status': ContractHour.PENDING_STATUS,
                'date_approved': datetime.date.today(),
            })
            ch.clean()

    def test_default_date_approved(self):
        # If saved with status approved and no date approved,
        # it sets it to today
        ch = self.create_contract_hour({
            'status': ContractHour.APPROVED_STATUS,
            'date_approved': None,
        })
        ch = ContractHour.objects.get(pk=ch.pk)
        self.assertEqual(datetime.date.today(), ch.date_approved)


class ContractHourEmailTestCase(TimepieceDataTestCase):

    def test_save_pending_calls_send_email(self):
        with mock.patch('timepiece.contracts.models.ContractHour._send_mail') as send_mail:
            self.create_contract_hour({
                'status': ContractHour.PENDING_STATUS
            })
        self.assertTrue(send_mail.called)
        (subject, ctx) = send_mail.call_args[0]
        self.assertTrue(subject.startswith("New"))

    def test_save_approved_does_not_call_send_email(self):
        with mock.patch('timepiece.contracts.models.ContractHour._send_mail') as send_mail:
            self.create_contract_hour({
                'status': ContractHour.APPROVED_STATUS
            })
        self.assertFalse(send_mail.called)

    def test_delete_pending_calls_send_email(self):
        ch = self.create_contract_hour({
            'status': ContractHour.PENDING_STATUS
        })
        with mock.patch('timepiece.contracts.models.ContractHour._send_mail') as send_mail:
            ch.delete()
        self.assertTrue(send_mail.called)
        (subject, ctx) = send_mail.call_args[0]
        self.assertTrue(subject.startswith("Deleted"))

    def test_change_pending_calls_send_email(self):
        ch = self.create_contract_hour({
            'status': ContractHour.PENDING_STATUS
        })
        with mock.patch('timepiece.contracts.models.ContractHour._send_mail') as send_mail:
            ch.save()
        self.assertTrue(send_mail.called)
        (subject, ctx) = send_mail.call_args[0]
        self.assertTrue(subject.startswith("Changed"))
