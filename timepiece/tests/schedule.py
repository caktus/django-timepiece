import datetime
from dateutil.relativedelta import relativedelta
import json
import mock

from timepiece import utils
from timepiece.forms import ScheduleAssignmentForm
from timepiece.models import ScheduleAssignment, Project
from timepiece.tests.base import TimepieceDataTestCase


__all__ = ['ScheduleTestBase', 'ScheduleViewTestCase', 'ScheduleEditTestCase',
        'ScheduleAjaxTestCase', 'ScheduleAssignmentModelTestCase',
        'ScheduleAssignmentFormTestCase']


class ScheduleAssignmentModelTestCase(TimepieceDataTestCase):

    def test_week_start(self):
        """week_start should always save to Monday of the given week."""
        project = self.create_project()
        monday = datetime.date(2012, 7, 16)
        for i in range(7):
            date = monday + relativedelta(days=i)
            assignment = ScheduleAssignment.objects.create(
                    week_start=date, project=project,
                    user=self.user)
            self.assertEquals(assignment.week_start.date(), monday)
            ScheduleAssignment.objects.all().delete()


class ScheduleAssignmentFormTestCase(TimepieceDataTestCase):

    def setUp(self):
        self.published = self.create_schedule_assignment(published=True)
        self.unpublished = self.create_schedule_assignment(published=False)
        self.data = {
            'week_start': utils.get_week_start().date(),
            'user': self.create_user().pk,
            'project': self.create_project().pk,
            'hours': 10,
        }

    def test_save_published(self):
        """Published entry should be saved as unpublished."""
        form = ScheduleAssignmentForm(data=self.data, instance=self.published)
        self.assertTrue(form.is_valid(), form.errors)
        assignment = form.save()
        self.assertFalse(assignment.published)

    def test_save_unpublished(self):
        """Unpublished entry should be saved as unpublished."""
        form = ScheduleAssignmentForm(data=self.data, instance=self.unpublished)
        self.assertTrue(form.is_valid(), form.errors)
        assignment = form.save()
        self.assertFalse(assignment.published)

    def test_save_new(self):
        """New entry should be saved as unpublished."""
        form = ScheduleAssignmentForm(data=self.data)
        self.assertTrue(form.is_valid(), form.errors)
        assignment = form.save()
        self.assertFalse(assignment.published)


class ScheduleTestBase(TimepieceDataTestCase):
    """Base test set up for all schedule view tests."""

    def setUp(self):
        self.permissions = self.get_permissions()
        self.user = self.create_user('user', 'u@abc.com', 'abc',
                user_permissions=self.permissions)
        self.client.login(username='user', password='abc')
        self.user2 = self.create_user()

        self.work_activities = self.create_activity_group('Work')
        self.leave_activities = self.create_activity_group('Leave')
        self.all_activities = self.create_activity_group('All')

        self.tracked_status = self.create_project_status(data={
            'label': 'Current',
            'billable': True,
            'enable_timetracking': True,
        })
        self.tracked_type = self.create_project_type(data={
            'label': 'Tracked',
            'billable': True,
            'enable_timetracking': True,
        })
        self.tracked_project = self.create_project(True, 'Tracked', {
            'type': self.tracked_type,
            'status': self.tracked_status,
            'activity_group': self.work_activities,
        })

        self.untracked_status = self.create_project_status(data={
            'label': 'Closed',
            'billable': False,
            'enable_timetracking': False,
        })
        self.untracked_type = self.create_project_type(data={
            'label': 'Untracked',
            'billable': False,
            'enable_timetracking': False,
        })
        self.untracked_project = self.create_project(True, 'Untracked', {
            'type': self.untracked_type,
            'status': self.untracked_status,
            'activity_group': self.all_activities,
        })

        self.this_week = utils.get_week_start().date()
        self.prev_week = self.this_week - relativedelta(days=7)
        self.next_week = self.this_week + relativedelta(days=7)
        self.get_kwargs = {
            'week_start': self._format(self.this_week),
        }

        self.prev_week_assignments = [
            self.create_schedule_assignment(week_start=self.prev_week,
                    project=self.tracked_project, user=self.user, hours=2),
            self.create_schedule_assignment(week_start=self.prev_week,
                    project=self.tracked_project, user=self.user2, hours=4),
        ]
        self.this_week_assignments = [
            self.create_schedule_assignment(week_start=self.this_week,
                    project=self.tracked_project, user=self.user, hours=15),
            self.create_schedule_assignment(week_start=self.this_week,
                    project=self.tracked_project, user=self.user2, hours=20),
        ]
        self.all_assignments = self.prev_week_assignments + \
                self.this_week_assignments

    def _format(self, week):
        return week.strftime('%Y-%m-%d')


class ScheduleViewTestCase(ScheduleTestBase):
    url_name = 'view_schedule'
    perm_names = [('timepiece', 'can_clock_in')]

    def test_no_permission(self):
        """Permission is required to view the schedule."""
        self.user.user_permissions.all().delete()
        response = self._get()
        self.assertEquals(response.status_code, 302)  # redirect to login

    def test_default_filter(self):
        """Schedule should show this week's published assignments."""
        self.this_week_assignments[0].published = True
        self.this_week_assignments[0].save()
        response = self._get(data={})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['week'], self.this_week)
        schedule = response.context['schedule']
        self.assertEquals(len(schedule), 1)  # 1 project
        proj_id, name, row = schedule[0]
        self.assertEquals(len(row), 1)  # 1 user
        self.assertEquals(row[0], self.this_week_assignments[0].hours)

    def test_week_filter(self):
        """Schedule should show assignments for Mon-Sun of specified week."""
        for assignment in self.prev_week_assignments:
            assignment.published = True
            assignment.save()
        get_kwargs = {'week_start': self._format(self.prev_week)}
        response = self._get(get_kwargs=get_kwargs)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['week'], self.prev_week)

        saved = ScheduleAssignment.objects.get_for_week(self.prev_week)
        users = response.context['users']
        schedule = response.context['schedule']
        count = 0
        for proj_id, name, assignments in schedule:
            for i, assignment in enumerate(assignments):
                if assignment:
                    count += 1
                    self.assertTrue(saved.filter(project__id=proj_id,
                            user__id=users[i][0], hours=assignment).exists())
        self.assertEquals(count, saved.count())

    def test_week_filter_midweek(self):
        """Filter corrects mid-week date to Monday of specified week."""
        wednesday = datetime.date(2012, 7, 4)
        monday = datetime.date(2012, 7, 2)
        data = {'week_start': self._format(wednesday)}
        response = self._get(data=data)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.context['week'], monday)

    def test_no_assignments(self):
        date = utils.get_week_start(datetime.date(2012, 3, 15))
        data = {'week_start': self._format(date)}
        response = self._get(data=data)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(len(response.context['users']), 0)
        self.assertEquals(len(response.context['schedule']), 0)

    def test_all_users_for_project(self):
        """Each project should have assignments for every user."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        users = response.context['users']
        schedule = response.context['schedule']
        for proj_id, name, assignments in schedule:
            self.assertEquals(len(assignments), len(users))


class ScheduleEditTestCase(ScheduleTestBase):
    url_name = 'edit_schedule'
    perm_names = [('timepiece', 'add_scheduleassignment')]

    def test_no_permission(self):
        """Permission is required to edit the schedule."""
        self.user.user_permissions.all().delete()
        response = self._get()
        self.assertEquals(response.status_code, 302)  # redirects to login

    def test_get(self):
        """GET returns a response with basic information in it."""
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertTrue('form' in response.context)
        self.assertTrue(response.context['week'], self.this_week)

    def test_duplicate(self):
        """Posting 'duplicate' copies the assignments from another week."""
        response = self._post(data={'duplicate': self._format(self.prev_week)})
        self.assertRedirectsNoFollow(response, self._url())
        for a in self.this_week_assignments:
            self.assertFalse(ScheduleAssignment.objects.filter(
                    pk=a.pk).exists())
        for a in self.prev_week_assignments:
            self.assertEquals(a, ScheduleAssignment.objects.get(pk=a.pk))
            self.assertTrue(ScheduleAssignment.objects.filter(user=a.user,
                    project=a.project, week_start=self.this_week,
                    hours=a.hours).exists())

    def test_duplicate_no_assignments(self):
        """If there are no assignmentss to duplicate, no operation occurs."""
        ScheduleAssignment.objects.filter(week_start=self.prev_week).delete()
        response = self._post(data={'duplicate': self._format(self.prev_week)})
        self.assertRedirectsNoFollow(response, self._url())
        self.assertEquals(ScheduleAssignment.objects.count(), 2)
        for a in self.this_week_assignments:
            self.assertEquals(a, ScheduleAssignment.objects.get(pk=a.pk))

    def test_publish(self):
        """Posting 'publish' publishes unpublished assignments for the week."""
        response = self._post(data={'publish': True})
        self.assertRedirectsNoFollow(response, self._url())
        self.assertEquals(ScheduleAssignment.objects.all().count(), 4)
        for a in self.this_week_assignments:
            # This week's assignments are now published.
            self.assertFalse(a.published)
            self.assertTrue(ScheduleAssignment.objects.get(pk=a.pk).published)
        for a in self.prev_week_assignments:
            # Other assignments remain the same.
            self.assertFalse(a.published)
            self.assertFalse(ScheduleAssignment.objects.get(pk=a.pk).published)

    def test_publish_no_assignments(self):
        """Posting 'publish' publishes unpublished assignments for the week."""
        ScheduleAssignment.objects.filter(week_start=self.this_week)\
                                  .update(published=True)
        response = self._post(data={'publish': True})
        self.assertRedirectsNoFollow(response, self._url())
        for a in self.all_assignments:
            self.assertEquals(a, ScheduleAssignment.objects.get(pk=a.pk))

    def test_duplicate_and_publish(self):
        """Posting 'publish' and 'duplicate' causes no operation."""
        response = self._post(data={
            'publish': True,
            'duplicate': self._format(self.prev_week),
        })
        self.assertRedirectsNoFollow(response, self._url())
        for a in self.all_assignments:
            self.assertEquals(a, ScheduleAssignment.objects.get(pk=a.pk))


class ScheduleAjaxTestCase(ScheduleTestBase):
    url_name = 'ajax_schedule'
    perm_names = [('timepiece', 'add_scheduleassignment')]

    def _post(self, *args, **kwargs):
        """
        By default, the Django test client interprets POST data as a
        dictionary. By using a different content type it will take the data as
        is.
        """
        if 'content_type' not in kwargs:
            kwargs['content_type'] = 'application/x-www-form-urlencoded'
        return super(ScheduleAjaxTestCase, self)._post(*args, **kwargs)

    def _delete(self, *args, **kwargs):
        """
        The test client in Django 1.4 requires key/value pairs for DELETE
        data. To get around this, we'll create a simple mock request and
        to test the basic functionality of the view. This is fixed in 1.5.
        """
        # Just use the default if data is not given.
        if 'data' not in kwargs:
            return super(ScheduleAjaxTestCase, self)._delete(*args, **kwargs)

        from timepiece.views import ScheduleAjax
        request = mock.Mock()
        request.raw_post_data = kwargs['data']
        request.method = 'DELETE'
        request.GET = kwargs.get('get_kwargs', None) or {}
        view = ScheduleAjax()
        return view.dispatch(request)

    def test_no_permission(self):
        """Permission is required to use the schedule AJAX view."""
        self.user.user_permissions.all().delete()
        methods = ['GET', 'POST', 'DELETE']
        functions = [self._get, self._post, self._delete]
        for method, _send in zip(methods, functions):
            response = _send()
            self.assertEquals(response.status_code, 302,
                    '{0} should redirect to login'.format(method))

    def test_get(self):
        """GET returns complete lists of assignments, projects, & users."""
        self.user3 = self.create_user(is_superuser=True)
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'application/json')
        content = json.loads(response.content)
        assignments = content['assignments']
        self.assertTrue(len(assignments), 4)
        for a in assignments:
            saved = ScheduleAssignment.objects.get(pk=a['id'])
            self.assertEquals(a['project__id'], saved.project.pk)
            self.assertEquals(a['user__id'], saved.user.pk)
            self.assertEquals(a['hours'], saved.hours)
        all_users = content['all_users']
        self.assertEquals(len(all_users), 1)
        self.assertTrue(all_users[0]['id'], self.user3.pk)
        all_projects = content['all_projects']
        self.assertTrue(len(all_projects), 2)
        for p in all_projects:
            saved = Project.objects.get(pk=p['id'])

    def test_get_no_assignments(self):
        """GET returns complete list of assignments, projects, & users."""
        self.user3 = self.create_user(is_superuser=True)
        ScheduleAssignment.objects.all().delete()
        response = self._get()
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'application/json')
        content = json.loads(response.content)
        assignments = content['assignments']
        self.assertEquals(len(assignments), 0)
        all_users = content['all_users']
        self.assertEquals(len(all_users), 1)
        self.assertTrue(all_users[0]['id'], self.user3.pk)
        all_projects = content['all_projects']
        self.assertTrue(len(all_projects), 2)
        for p in all_projects:
            saved = Project.objects.get(pk=p['id'])

    def test_delete(self):
        """DELETE should delete all assignments with given ids."""
        pks = [self.this_week_assignments[0].pk]
        response = self._delete(data=json.dumps(pks))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'application/json')
        content = json.loads(response.content)
        self.assertEquals(content, pks)
        saved = ScheduleAssignment.objects.all()
        self.assertEqual(saved.count(), 3)
        self.assertTrue(self.this_week_assignments[1] in saved)
        self.assertTrue(self.prev_week_assignments[0] in saved)
        self.assertTrue(self.prev_week_assignments[1] in saved)

    def test_delete_different_week(self):
        """DELETE should only work on assignments for current week."""
        pks = [self.prev_week_assignments[0].pk]
        response = self._delete(data=json.dumps(pks))
        self.assertEquals(response.status_code, 500)
        self.assertEquals(ScheduleAssignment.objects.count(), 4)

    def test_delete_bad_format(self):
        """DELETE returns 500 response if data is not JSON-encoded."""
        response = self._delete(data='bad')
        self.assertEquals(response.status_code, 500)
        self.assertEquals(ScheduleAssignment.objects.count(), 4)

    def test_delete_non_existing(self):
        """DELETE returns 500 response if an assignment doesn't exist."""
        pks = [123]
        response = self._delete(data=json.dumps(pks))
        self.assertEquals(response.status_code, 500)
        self.assertEquals(ScheduleAssignment.objects.count(), 4)

    def test_post_bad_format(self):
        """POST returns 500 response if data is not JSON-encoded."""
        response = self._delete(data='bad')
        self.assertEquals(response.status_code, 500)
        self.assertEquals(ScheduleAssignment.objects.count(), 4)

    def test_post_create(self):
        """POST assignment map w/no id should create a new assignment."""
        project = self.create_project()
        data = [{'project': project.pk, 'user': self.user.pk, 'hours': 5}]
        response = self._post(data=json.dumps(data))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'application/json')
        content = json.loads(response.content)
        self.assertEquals(ScheduleAssignment.objects.count(), 5)
        new = ScheduleAssignment.objects.get(pk=content[0])
        self.assertEquals(new.project.pk, project.pk)
        self.assertEquals(new.user.pk, self.user.pk)
        self.assertEquals(new.week_start, self.this_week)
        self.assertEquals(new.hours, 5)

    def test_post_create_duplicate(self):
        """
        Assignment shouldn't be created if one already exists for project,
        user, and week.
        """
        data = [{'project': self.tracked_project.pk, 'user': self.user.pk,
                'hours': 5}]
        response = self._post(data=json.dumps(data))
        self.assertEquals(response.status_code, 500)
        self.assertEquals(ScheduleAssignment.objects.count(), 4)

    def test_post_create_0_hours(self):
        """Assignment should not be created if 0 hours are specified."""
        project = self.create_project()
        data = [{'project': project.pk, 'user': self.user.pk, 'hours': 0}]
        response = self._post(data=json.dumps(data))
        self.assertEquals(response.status_code, 500)
        self.assertEquals(ScheduleAssignment.objects.count(), 4)

    def test_post_update(self):
        """POST assignment map w/pk should update existing assignment."""
        assignment = self.this_week_assignments[0]
        data = [{'id': assignment.pk, 'project': assignment.project.pk,
                'user': assignment.user.pk, 'hours': assignment.hours + 10}]
        response = self._post(data=json.dumps(data))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'application/json')
        content = json.loads(response.content)
        self.assertEquals(content, [assignment.pk])
        self.assertEquals(ScheduleAssignment.objects.count(), 4)
        saved = ScheduleAssignment.objects.get(pk=assignment.pk)
        self.assertEquals(saved.hours, assignment.hours + 10)

    def test_post_update_non_existing(self):
        """POST returns 500 response if assignment to update does not exist."""
        data = [{'id': 123, 'project': self.tracked_project.pk,
                'user': self.user.pk, 'hours': 15}]
        response = self._post(data=json.dumps(data))
        self.assertEquals(response.status_code, 500)
        self.assertEquals(ScheduleAssignment.objects.count(), 4)

    def test_post_update_last_week(self):
        """POST can only update assignment from current week."""
        assignment = self.prev_week_assignments[0]
        data = [{'id': assignment.pk, 'project': assignment.project.pk,
                'user': assignment.user.pk, 'hours': assignment.hours + 10}]
        response = self._post(data=json.dumps(data))
        self.assertEquals(response.status_code, 500)
        self.assertEquals(ScheduleAssignment.objects.count(), 4)
        saved = ScheduleAssignment.objects.get(pk=assignment.pk)
        self.assertEquals(saved.hours, assignment.hours)

    def test_post_multiple(self):
        """POST can accept multiple entries to create/update."""
        project = self.create_project()
        assignment = self.this_week_assignments[0]
        data = [
            {'project': project.pk, 'user': self.user.pk, 'hours': 5},
            {'id': assignment.pk, 'project': assignment.project.pk,
                    'user': assignment.user.pk,
                    'hours': assignment.hours + 10},
        ]
        response = self._post(data=json.dumps(data))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response['Content-Type'], 'application/json')
        content = json.loads(response.content)
        new = ScheduleAssignment.objects.get(project=project, user=self.user,
                week_start=self.this_week, hours=5)
        self.assertEquals(content, [new.pk, assignment.pk])

    def test_post_multiple_bad_format(self):
        """No changes occur if one part has bad data."""
        project = self.create_project()
        assignment = self.this_week_assignments[0]
        data = [
            {'project': project.pk, 'user': self.user.pk, 'hours': 5},
            {'id': 123, 'project': assignment.project.pk,
                    'user': assignment.user.pk, 'hours': 20},
        ]
        response = self._post(data=json.dumps(data))
        self.assertEquals(response.status_code, 500)
        self.assertEquals(ScheduleAssignment.objects.count(), 4)
