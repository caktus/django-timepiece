import datetime
from dateutil.relativedelta import relativedelta
import json

from django.contrib.auth.models import Permission

from timepiece import models as timepiece
from timepiece.tests.base import TimepieceDataTestCase


class TestProductivityReport(TimepieceDataTestCase):
    url_name = 'report_productivity'

    def setUp(self):
        self.username = 'test_user'
        self.password = 'password'
        self.user = self.create_user(username=self.username,
                password=self.password)
        self.permission = Permission.objects.get(codename='view_entry_summary')
        self.user.user_permissions.add(self.permission)
        self.client.login(username=self.username, password=self.password)

        self.project = self.create_project()
        self.users = []
        self.users.append(self.create_user(first_name='User', last_name='1'))
        self.users.append(self.create_user(first_name='User', last_name='2'))
        self.users.append(self.create_user(first_name='User', last_name='3'))
        self.weeks = []
        self.weeks.append(datetime.datetime(2012, 9, 24))
        self.weeks.append(datetime.datetime(2012, 10, 1))
        self.weeks.append(datetime.datetime(2012, 10, 8))
        self.weeks.append(datetime.datetime(2012, 10, 15))

        self._create_entries()
        self._create_assignments()

    def _create_entries(self):
        for start_time in (self.weeks[1], self.weeks[3]):
            for user in (self.users[1], self.users[2]):
                end_time = start_time + relativedelta(hours=2)
                data = {'user': user, 'start_time': start_time,
                        'end_time': end_time, 'project': self.project}
                self.create_entry(data)

    def _create_assignments(self):
        for week_start in (self.weeks[0], self.weeks[1]):
            for user in (self.users[0], self.users[1]):
                data = {'user': user, 'week_start': week_start,
                        'project': self.project, 'hours': 2}
                self.create_project_hours_entry(**data)

    def _unpack(self, response):
        form = response.context['form']
        report = json.loads(response.context['report'])
        organize_by = response.context['type']
        worked = response.context['total_worked']
        assigned = response.context['total_assigned']
        return form, report, organize_by, worked, assigned

    def _check_row(self, row, correct):
        self.assertEqual(len(row), 3)
        self.assertEqual(row[0], correct[0])
        self.assertEqual(float(row[1]), correct[1])
        self.assertEqual(float(row[2]), correct[2])

    def test_not_authenticated(self):
        """User must be logged in to see this report."""
        self.client.logout()
        response = self._get()
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_no_permission(self):
        """This report requires permission to view entry summaries."""
        self.user.user_permissions.remove(self.permission)
        response = self._get()
        self.assertEqual(response.status_code, 302)  # Redirects to login

    def test_retrieval(self):
        """No report data should be returned upon initial retrieval."""
        response = self._get()
        self.assertEqual(response.status_code, 200)
        form, report, organize_by, worked, assigned = self._unpack(response)
        self.assertEqual(len(form.errors), 0)
        self.assertEqual(len(report), 0)
        self.assertEqual(organize_by, '')
        self.assertEqual(float(worked), 0.0)
        self.assertEqual(float(assigned), 0.0)

    def test_no_project(self):
        """Form requires specification of project."""
        data = {'organize_by': 'week'}
        response = self._get(data=data)
        self.assertEqual(response.status_code, 200)
        form, report, organize_by, worked, assigned = self._unpack(response)
        self.assertEqual(len(form.errors), 1)
        self.assertTrue('project' in form.errors)
        self.assertEqual(len(report), 0)
        self.assertEqual(organize_by, '')
        self.assertEqual(float(worked), 0.0)
        self.assertEqual(float(assigned), 0.0)

    def test_invalid_project_id(self):
        """Form requires specification of valid project."""
        data = {'organize_by': 'week', 'project_1': 12345}
        response = self._get(data=data)
        self.assertEqual(response.status_code, 200)
        form, report, organize_by, worked, assigned = self._unpack(response)
        self.assertEqual(len(form.errors), 1)
        self.assertTrue('project' in form.errors)
        self.assertEqual(len(report), 0)
        self.assertEqual(organize_by, '')
        self.assertEqual(float(worked), 0.0)
        self.assertEqual(float(assigned), 0.0)

    def test_no_organize_by(self):
        """Form requires specification of organization method."""
        data = {'project_1': self.project.pk}
        response = self._get(data=data)
        self.assertEqual(response.status_code, 200)
        form, report, organize_by, worked, assigned = self._unpack(response)
        self.assertEqual(len(form.errors), 1)
        self.assertTrue('organize_by' in form.errors)
        self.assertEqual(len(report), 0)
        self.assertEqual(organize_by, '')
        self.assertEqual(float(worked), 0.0)
        self.assertEqual(float(assigned), 0.0)

    def test_invalid_organize_by(self):
        """Form requires specification of valid organization method."""
        data = {'project_1': self.project.pk, 'organize_by': 'invalid'}
        response = self._get(data=data)
        self.assertEqual(response.status_code, 200)
        form, report, organize_by, worked, assigned = self._unpack(response)
        self.assertEqual(len(form.errors), 1)
        self.assertTrue('organize_by' in form.errors)
        self.assertEqual(len(report), 0)
        self.assertEqual(organize_by, '')
        self.assertEqual(float(worked), 0.0)
        self.assertEqual(float(assigned), 0.0)

    def test_no_data(self):
        """If no data, report should contain header row only."""
        timepiece.Entry.objects.filter(project=self.project).delete()
        timepiece.ProjectHours.objects.filter(project=self.project).delete()
        data = {'project_1': self.project.pk, 'organize_by': 'week'}
        response = self._get(data=data)
        self.assertEqual(response.status_code, 200)
        form, report, organize_by, worked, assigned = self._unpack(response)
        self.assertEqual(len(form.errors), 0)
        self.assertEqual(len(report), 1)
        self.assertEqual(organize_by, 'week')
        self.assertEqual(float(worked), 0.0)
        self.assertEqual(float(assigned), 0.0)

    def test_organize_by_week(self):
        """Report should contain hours per week on the project."""
        data = {'project_1': self.project.pk, 'organize_by': 'week'}
        response = self._get(data=data)
        self.assertEqual(response.status_code, 200)
        form, report, organize_by, worked, assigned = self._unpack(response)
        self.assertEqual(len(form.errors), 0)
        self.assertEqual(organize_by, 'week')
        self.assertEqual(float(worked), 8.0)
        self.assertEqual(float(assigned), 8.0)
        self.assertEqual(len(report), 1 + 4)  # Include header row
        self._check_row(report[1], ['2012-09-24', 0.0, 4.0])
        self._check_row(report[2], ['2012-10-01', 4.0, 4.0])
        self._check_row(report[3], ['2012-10-08', 0.0, 0.0])
        self._check_row(report[4], ['2012-10-15', 4.0, 0.0])

    def test_organize_by_users(self):
        """Report should contain hours per peron on the project."""
        data = {'project_1': self.project.pk, 'organize_by': 'user'}
        response = self._get(data=data)
        self.assertEqual(response.status_code, 200)
        form, report, organize_by, worked, assigned = self._unpack(response)
        self.assertEqual(len(form.errors), 0)
        self.assertEqual(organize_by, 'user')
        self.assertEqual(float(worked), 8.0)
        self.assertEqual(float(assigned), 8.0)
        self.assertEqual(len(report), 1 + 3)  # Include header row
        self._check_row(report[1], ['User 1', 0.0, 4.0])
        self._check_row(report[2], ['User 2', 4.0, 4.0])
        self._check_row(report[3], ['User 3', 4.0, 0.0])

    def test_export(self):
        """Data should be exported in CSV format."""
        data = {'project_1': self.project.pk, 'organize_by': 'week',
                'export': True}
        response = self._get(data=data)
        self.assertEqual(response.status_code, 200)
        data = dict(response.items())
        self.assertEqual(data['Content-Type'], 'text/csv')
        disposition = 'attachment; filename={0}_productivity.csv'.format(
                self.project.name)
        self.assertTrue(data['Content-Disposition'].startswith(disposition))
        report = response.content.splitlines()
        self.assertEqual(len(report), 1 + 4)  # Include header row
        self._check_row(report[1].split(','), ['2012-09-24', 0.0, 4.0])
        self._check_row(report[2].split(','), ['2012-10-01', 4.0, 4.0])
        self._check_row(report[3].split(','), ['2012-10-08', 0.0, 0.0])
        self._check_row(report[4].split(','), ['2012-10-15', 4.0, 0.0])
