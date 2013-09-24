import datetime
import mock

from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase

from timepiece.contracts.models import ProjectContract, ContractHour
from timepiece.tests.base import ViewTestMixin
from timepiece.tests import factories


class ContractListTestCase(ViewTestMixin, TestCase):
    url_name = 'list_contracts'
    perm_names = [('contracts', 'add_projectcontract')]

    def setUp(self):
        get_perm = lambda ct, n: Permission.objects.get(
                content_type__app_label=ct, codename=n)
        self.permissions = [get_perm(*perm) for perm in self.perm_names]

        self.user = factories.User()
        self.user.user_permissions.add(*self.permissions)
        self.login_user(self.user)

        self.project1 = factories.Project()
        self.project2 = factories.Project()
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
        correct_contract = factories.ProjectContract(projects=self.projects,
                status=ProjectContract.STATUS_CURRENT)
        response = self._get()
        self.assertEqual(response.status_code, 200)
        contracts = response.context['contracts']
        self.assertEqual(len(contracts), 1)
        self.assertTrue(correct_contract in contracts)

    def test_contracts(self):
        """List should return all current contracts."""
        correct_contracts = [factories.ProjectContract(projects=self.projects,
                status=ProjectContract.STATUS_CURRENT) for i in range(3)]
        response = self._get()
        self.assertEqual(response.status_code, 200)
        contracts = response.context['contracts']
        self.assertEqual(len(contracts), 3)
        for i in range(3):
            self.assertTrue(correct_contracts[i] in contracts)

    def test_non_current_contracts(self):
        """List should return all current contracts."""
        complete_contract = factories.ProjectContract(projects=self.projects,
                status=ProjectContract.STATUS_COMPLETE)
        upcoming_contract = factories.ProjectContract(projects=self.projects,
                status=ProjectContract.STATUS_UPCOMING)
        response = self._get()
        self.assertEqual(response.status_code, 200)
        contracts = response.context['contracts']
        self.assertEqual(len(contracts), 0)


class ContractViewTestCase(ViewTestMixin, TestCase):
    url_name = 'view_contract'
    perm_names = [('contracts', 'add_projectcontract')]

    @property
    def url_args(self):
        return (self.contract.pk,)

    def setUp(self):
        get_perm = lambda ct, n: Permission.objects.get(
                content_type__app_label=ct, codename=n)
        self.permissions = [get_perm(*perm) for perm in self.perm_names]

        self.user = factories.User()
        self.user.user_permissions.add(*self.permissions)
        self.login_user(self.user)

        self.project1 = factories.Project()
        self.project2 = factories.Project()
        self.projects = [self.project1, self.project2]

        self.contract = factories.ProjectContract(projects=self.projects)

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
        contract = factories.ProjectContract(projects=self.projects,
                status=ProjectContract.STATUS_CURRENT)
        response = self._get(url_args=(contract.pk,))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(contract, response.context['contract'])

    def test_upcoming_contract(self):
        contract = factories.ProjectContract(projects=self.projects,
                status=ProjectContract.STATUS_UPCOMING)
        response = self._get(url_args=(contract.pk,))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(contract, response.context['contract'])

    def test_complete_contract(self):
        contract = factories.ProjectContract(projects=self.projects,
                status=ProjectContract.STATUS_COMPLETE)
        response = self._get(url_args=(contract.pk,))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(contract, response.context['contract'])


class ContractHourTestCase(TestCase):

    def test_defaults(self):
        contract_hour = ContractHour()
        self.assertEqual(0, contract_hour.hours)
        self.assertEqual(ContractHour.PENDING_STATUS, contract_hour.status)

    def test_contracted_hours(self):
        # If we create some Contract Hour objects and then go to the
        # project contract and get contracted_hours(), it gives the sum
        # of the hours
        pc = factories.ProjectContract(contract_hours=4)
        self.assertEqual(4, pc.contracted_hours())
        self.assertEqual(0, pc.pending_hours())

    def test_pending_hours(self):
        # If we create some pending Contract Hour objects and then go to the
        # project contract and get pending_hours(), it gives the sum
        # of the hours
        pc = factories.ProjectContract(contract_hours=4)
        ch = factories.ContractHour(contract=pc, hours=27,
                status=ContractHour.PENDING_STATUS)
        self.assertEqual(4, pc.contracted_hours())
        self.assertEqual(27, pc.pending_hours())
        ch.delete()
        self.assertEqual(4, pc.contracted_hours())
        self.assertEqual(0, pc.pending_hours())

    def test_validation(self):
        with self.assertRaises(ValidationError):
            ch = factories.ContractHour(
                    status=ContractHour.PENDING_STATUS,
                    date_approved=datetime.date.today())
            ch.clean()

    def test_default_date_approved(self):
        # If saved with status approved and no date approved,
        # it sets it to today
        ch = factories.ContractHour(
                status=ContractHour.APPROVED_STATUS,
                date_approved=None)
        ch = ContractHour.objects.get(pk=ch.pk)
        self.assertEqual(datetime.date.today(), ch.date_approved)

    def test_fraction_hours(self):
        # fraction_hours returns what fraction of the contracted hours
        # have been worked
        contracted_hours = 0
        pc = factories.ProjectContract(contract_hours=contracted_hours)
        # If contracted hours 0, return 0 (don't div/0)
        self.assertEqual(0.0, pc.fraction_hours)
        contracted_hours = 10.0
        pc = factories.ProjectContract(contract_hours=contracted_hours)
        # If contracted hours non-zero, worked hours 0, return 0
        self.assertEqual(0.0, pc.fraction_hours)
        # Now do some work
        pc._worked = 5.0
        self.assertEqual(0.5, pc.fraction_hours)


    def test_fraction_schedule(self):
        # fraction_schedule returns what fraction of the contract period
        # has elapsed - if the contract is current
        one_month = datetime.timedelta(days=30)
        today = datetime.date.today()
        last_month = today - one_month
        next_month = today + one_month
        pc = factories.ProjectContract(
            status=ProjectContract.STATUS_UPCOMING, start_date=last_month,
            end_date=next_month
        )
        self.assertEqual(0.0, pc.fraction_schedule)
        pc.status = ProjectContract.STATUS_COMPLETE
        self.assertEqual(0.0, pc.fraction_schedule)
        pc.status = ProjectContract.STATUS_CURRENT
        self.assertEqual(0.5, pc.fraction_schedule)
        # Just to be perverse, a contract in current state whose start
        # date hasn't arrived yet
        pc.start_date = today + datetime.timedelta(days=2)
        self.assertEqual(0.0, pc.fraction_schedule)

    def test_get_absolute_url(self):
        ch = factories.ContractHour.create()
        url = '/admin/contracts/contracthour/%d/' % ch.pk
        self.assertEqual(url, ch.get_absolute_url())


class ContractHourEmailTestCase(TestCase):

    def test_save_pending_calls_send_email(self):
        with mock.patch('timepiece.contracts.models.ContractHour._send_mail') as send_mail:
            factories.ContractHour(status=ContractHour.PENDING_STATUS)
        self.assertTrue(send_mail.called)
        (subject, ctx) = send_mail.call_args[0]
        self.assertTrue(subject.startswith("New"))

    def test_save_approved_does_not_call_send_email(self):
        with mock.patch('timepiece.contracts.models.ContractHour._send_mail') as send_mail:
            factories.ContractHour(status=ContractHour.APPROVED_STATUS)
        self.assertFalse(send_mail.called)

    def test_delete_pending_calls_send_email(self):
        ch = factories.ContractHour(status=ContractHour.PENDING_STATUS)
        with mock.patch('timepiece.contracts.models.ContractHour._send_mail') as send_mail:
            ch.delete()
        self.assertTrue(send_mail.called)
        (subject, ctx) = send_mail.call_args[0]
        self.assertTrue(subject.startswith("Deleted"))

    def test_change_pending_calls_send_email(self):
        ch = factories.ContractHour(status=ContractHour.PENDING_STATUS)
        with mock.patch('timepiece.contracts.models.ContractHour._send_mail') as send_mail:
            ch.save()
        self.assertTrue(send_mail.called)
        (subject, ctx) = send_mail.call_args[0]
        self.assertTrue(subject.startswith("Changed"))
