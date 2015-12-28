import datetime
import mock

from dateutil.relativedelta import relativedelta

from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from timepiece.contracts.models import ProjectContract, ContractHour
from timepiece.entries.models import Entry
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
        correct_contract = factories.ProjectContract(
            projects=self.projects, status=ProjectContract.STATUS_CURRENT)
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
        factories.ProjectContract(
            projects=self.projects, status=ProjectContract.STATUS_COMPLETE)
        factories.ProjectContract(
            projects=self.projects, status=ProjectContract.STATUS_UPCOMING)
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
        contract = factories.ProjectContract(
            projects=self.projects, status=ProjectContract.STATUS_CURRENT)
        response = self._get(url_args=(contract.pk,))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(contract, response.context['contract'])

    def test_upcoming_contract(self):
        contract = factories.ProjectContract(
            projects=self.projects, status=ProjectContract.STATUS_UPCOMING)
        response = self._get(url_args=(contract.pk,))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(contract, response.context['contract'])

    def test_complete_contract(self):
        contract = factories.ProjectContract(
            projects=self.projects, status=ProjectContract.STATUS_COMPLETE)
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
        ch = factories.ContractHour(
            contract=pc, hours=27, status=ContractHour.PENDING_STATUS)
        self.assertEqual(4, pc.contracted_hours())
        self.assertEqual(27, pc.pending_hours())
        ch.delete()
        self.assertEqual(4, pc.contracted_hours())
        self.assertEqual(0, pc.pending_hours())

    def test_validation(self):
        with self.assertRaises(ValidationError):
            ch = factories.ContractHour(
                status=ContractHour.PENDING_STATUS, date_approved=datetime.date.today())
            ch.clean()

    def test_default_date_approved(self):
        # If saved with status approved and no date approved,
        # it sets it to today
        ch = factories.ContractHour(
            status=ContractHour.APPROVED_STATUS, date_approved=None)
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


class ProjectContractEntryTestCase(TestCase):
    """
    Set up two projects and two contracts. The relationship diagram looks like a Z,
    with the following instances:

           Project A ----- Contract 1
                          /
              Project B  /______Contract 2

    User A logs one hour per day to Project A and user B logs one hour per day to
    project B.
    """

    def setUp(self):
        super(ProjectContractEntryTestCase, self).setUp()
        self.user_a = factories.User(username='userA')
        self.user_b = factories.User(username='userB')
        self.project_a = factories.Project(
            type__enable_timetracking=True,
            status__enable_timetracking=True,
            name='Project A')
        self.project_b = factories.Project(
            type__enable_timetracking=True,
            status__enable_timetracking=True,
            name='Project B')

        self.contract1 = factories.ProjectContract(
            name='Contract 1',
            projects=[self.project_a, self.project_b],
            status=ProjectContract.STATUS_CURRENT,
            start_date=timezone.now().replace(
                hour=0, minute=0, second=0, microsecond=0) - relativedelta(days=16),
            end_date=timezone.now().replace(
                hour=0, minute=0, second=0, microsecond=0) - relativedelta(days=12),
            )

        self.contract2 = factories.ProjectContract(
            name='Contract 2',
            projects=[self.project_b],
            status=ProjectContract.STATUS_CURRENT,
            start_date=timezone.now().replace(
                hour=0, minute=0, second=0, microsecond=0) - relativedelta(days=8),
            end_date=timezone.now().replace(
                hour=0, minute=0, second=0, microsecond=0) - relativedelta(days=4),
            )

        for x in range(20):
            factories.Entry(**{
                'user': self.user_a,
                'project': self.project_a,
                'start_time': timezone.now() - relativedelta(days=x),
                'end_time':  (timezone.now() - relativedelta(days=x)) + relativedelta(hours=1),
                'seconds_paused': 0,
                'status': Entry.UNVERIFIED,
            })

            factories.Entry(**{
                'user': self.user_b,
                'project': self.project_b,
                'start_time': timezone.now() - relativedelta(days=x),
                'end_time':  (timezone.now() - relativedelta(days=x)) + relativedelta(hours=1),
                'seconds_paused': 0,
                'status': Entry.UNVERIFIED,
            })

    def testContract1PreValues(self):
        self.assertEqual(self.contract1.pre_launch_entries.count(), 6)
        self.assertEqual(self.contract1.pre_launch_hours_worked, 6.0)

    def testContract1Values(self):
        self.assertEqual(self.contract1.entries.count(), 10)
        self.assertEqual(self.contract1.hours_worked, 10.0)

    def testContract1PostValues(self):
        self.assertEqual(self.contract1.post_launch_entries.count(), 24)
        self.assertEqual(self.contract1.post_launch_hours_worked, 24.0)

    def testContract2PreValues(self):
        self.assertEqual(self.contract2.pre_launch_entries.count(), 11)
        self.assertEqual(self.contract2.pre_launch_hours_worked, 11.0)

    def testContract2Values(self):
        self.assertEqual(self.contract2.entries.count(), 5)
        self.assertEqual(self.contract2.hours_worked, 5.0)

    def testContract2PostValues(self):
        self.assertEqual(self.contract2.post_launch_entries.count(), 4)
        self.assertEqual(self.contract2.post_launch_hours_worked, 4.0)
