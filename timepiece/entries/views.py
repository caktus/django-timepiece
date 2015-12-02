from copy import deepcopy
import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from itertools import groupby
import json

from six.moves.urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.core import exceptions
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View

from timepiece import utils
from timepiece.forms import DATE_FORM_FORMAT
from timepiece.utils.csv import DecimalEncoder
from timepiece.utils.views import cbv_decorator

from timepiece.crm.models import Project, UserProfile
from timepiece.entries.forms import (
    ClockInForm, ClockOutForm, AddUpdateEntryForm, ProjectHoursForm,
    ProjectHoursSearchForm)
from timepiece.entries.models import Entry, ProjectHours


class Dashboard(TemplateView):
    template_name = 'timepiece/dashboard.html'

    @method_decorator(login_required)
    def dispatch(self, request, active_tab, *args, **kwargs):
        self.active_tab = active_tab or 'progress'
        self.user = request.user
        return super(Dashboard, self).dispatch(request, *args, **kwargs)

    def get_dates(self):
        today = datetime.date.today()
        day = today
        if 'week_start' in self.request.GET:
            param = self.request.GET.get('week_start')
            try:
                day = datetime.datetime.strptime(param, '%Y-%m-%d').date()
            except:
                pass
        week_start = utils.get_week_start(day)
        week_end = week_start + relativedelta(days=6)
        return today, week_start, week_end

    def get_hours_per_week(self, user=None):
        """Retrieves the number of hours the user should work per week."""
        try:
            profile = UserProfile.objects.get(user=user or self.user)
        except UserProfile.DoesNotExist:
            profile = None
        return profile.hours_per_week if profile else Decimal('40.00')

    def get_context_data(self, *args, **kwargs):
        today, week_start, week_end = self.get_dates()

        # Query for the user's active entry if it exists.
        active_entry = utils.get_active_entry(self.user)

        # Process this week's entries to determine assignment progress.
        week_entries = Entry.objects.filter(user=self.user)
        week_entries = week_entries.timespan(week_start, span='week', current=True)
        week_entries = week_entries.select_related('project')
        assignments = ProjectHours.objects.filter(
            user=self.user, week_start=week_start.date())
        project_progress = self.process_progress(week_entries, assignments)

        # Total hours that the user is expected to clock this week.
        total_assigned = self.get_hours_per_week(self.user)
        total_worked = sum([p['worked'] for p in project_progress])

        # Others' active entries.
        others_active_entries = Entry.objects.filter(end_time__isnull=True)
        others_active_entries = others_active_entries.exclude(user=self.user)
        others_active_entries = others_active_entries.select_related('user', 'project', 'activity')

        return {
            'active_tab': self.active_tab,
            'today': today,
            'week_start': week_start.date(),
            'week_end': week_end.date(),
            'active_entry': active_entry,
            'total_assigned': total_assigned,
            'total_worked': total_worked,
            'project_progress': project_progress,
            'week_entries': week_entries,
            'others_active_entries': others_active_entries,
        }

    def process_progress(self, entries, assignments):
        """
        Returns a list of progress summary data (pk, name, hours worked, and
        hours assigned) for each project either worked or assigned.
        The list is ordered by project name.
        """
        # Determine all projects either worked or assigned.
        project_q = Q(id__in=assignments.values_list('project__id', flat=True))
        project_q |= Q(id__in=entries.values_list('project__id', flat=True))
        projects = Project.objects.filter(project_q).select_related('business')

        # Hours per project.
        project_data = {}
        for project in projects:
            try:
                assigned = assignments.get(project__id=project.pk).hours
            except ProjectHours.DoesNotExist:
                assigned = Decimal('0.00')
            project_data[project.pk] = {
                'project': project,
                'assigned': assigned,
                'worked': Decimal('0.00'),
            }

        for entry in entries:
            pk = entry.project_id
            hours = Decimal('%.2f' % (entry.get_total_seconds() / 3600.0))
            project_data[pk]['worked'] += hours

        # Sort by maximum of worked or assigned hours (highest first).
        key = lambda x: x['project'].name.lower()
        project_progress = sorted(project_data.values(), key=key)

        return project_progress


@permission_required('entries.can_clock_in')
@transaction.atomic
def clock_in(request):
    """For clocking the user into a project."""
    user = request.user
    # Lock the active entry for the duration of this transaction, to prevent
    # creating multiple active entries.
    active_entry = utils.get_active_entry(user, select_for_update=True)

    initial = dict([(k, v) for k, v in request.GET.items()])
    data = request.POST or None
    form = ClockInForm(data, initial=initial, user=user, active=active_entry)
    if form.is_valid():
        entry = form.save()
        message = 'You have clocked into {0} on {1}.'.format(
            entry.activity.name, entry.project)
        messages.info(request, message)
        return HttpResponseRedirect(reverse('dashboard'))

    return render(request, 'timepiece/entry/clock_in.html', {
        'form': form,
        'active': active_entry,
    })


@permission_required('entries.can_clock_out')
def clock_out(request):
    entry = utils.get_active_entry(request.user)
    if not entry:
        message = "Not clocked in"
        messages.info(request, message)
        return HttpResponseRedirect(reverse('dashboard'))
    if request.POST:
        form = ClockOutForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save()
            message = 'You have clocked out of {0} on {1}.'.format(
                entry.activity.name, entry.project)
            messages.info(request, message)
            return HttpResponseRedirect(reverse('dashboard'))
        else:
            message = 'Please correct the errors below.'
            messages.error(request, message)
    else:
        form = ClockOutForm(instance=entry)
    return render(request, 'timepiece/entry/clock_out.html', {
        'form': form,
        'entry': entry,
    })


@permission_required('entries.can_pause')
def toggle_pause(request):
    """Allow the user to pause and unpause the active entry."""
    entry = utils.get_active_entry(request.user)
    if not entry:
        raise Http404

    # toggle the paused state
    entry.toggle_paused()
    entry.save()

    # create a message that can be displayed to the user
    action = 'paused' if entry.is_paused else 'resumed'
    message = 'Your entry, {0} on {1}, has been {2}.'.format(
        entry.activity.name, entry.project, action)
    messages.info(request, message)

    # redirect to the log entry list
    return HttpResponseRedirect(reverse('dashboard'))


@permission_required('entries.change_entry')
def create_edit_entry(request, entry_id=None):
    if entry_id:
        try:
            entry = Entry.no_join.get(pk=entry_id)
        except Entry.DoesNotExist:
            entry = None
        else:
            if not (entry.is_editable or request.user.has_perm('entries.view_payroll_summary')):
                raise Http404
    else:
        entry = None

    entry_user = entry.user if entry else request.user
    if request.method == 'POST':
        form = AddUpdateEntryForm(data=request.POST, instance=entry, user=entry_user)
        if form.is_valid():
            entry = form.save()
            if entry_id:
                message = 'The entry has been updated successfully.'
            else:
                message = 'The entry has been created successfully.'
            messages.info(request, message)
            url = request.GET.get('next', reverse('dashboard'))
            return HttpResponseRedirect(url)
        else:
            message = 'Please fix the errors below.'
            messages.error(request, message)
    else:
        initial = dict([(k, request.GET[k]) for k in request.GET.keys()])
        form = AddUpdateEntryForm(instance=entry, user=entry_user, initial=initial)

    return render(request, 'timepiece/entry/create_edit.html', {
        'form': form,
        'entry': entry,
    })


@permission_required('entries.view_payroll_summary')
def reject_entry(request, entry_id):
    """
    Admins can reject an entry that has been verified or approved but not
    invoiced to set its status to 'unverified' for the user to fix.
    """
    return_url = request.GET.get('next', reverse('dashboard'))
    try:
        entry = Entry.no_join.get(pk=entry_id)
    except:
        message = 'No such log entry.'
        messages.error(request, message)
        return redirect(return_url)

    if entry.status == Entry.UNVERIFIED or entry.status == Entry.INVOICED:
        msg_text = 'This entry is unverified or is already invoiced.'
        messages.error(request, msg_text)
        return redirect(return_url)

    if request.POST.get('Yes'):
        entry.status = Entry.UNVERIFIED
        entry.save()
        msg_text = 'The entry\'s status was set to unverified.'
        messages.info(request, msg_text)
        return redirect(return_url)
    return render(request, 'timepiece/entry/reject.html', {
        'entry': entry,
        'next': request.GET.get('next'),
    })


@permission_required('entries.delete_entry')
def delete_entry(request, entry_id):
    """
    Give the user the ability to delete a log entry, with a confirmation
    beforehand.  If this method is invoked via a GET request, a form asking
    for a confirmation of intent will be presented to the user. If this method
    is invoked via a POST request, the entry will be deleted.
    """
    try:
        entry = Entry.no_join.get(pk=entry_id, user=request.user)
    except Entry.DoesNotExist:
        message = 'No such entry found.'
        messages.info(request, message)
        url = request.GET.get('next', reverse('dashboard'))
        return HttpResponseRedirect(url)

    if request.method == 'POST':
        key = request.POST.get('key', None)
        if key and key == entry.delete_key:
            entry.delete()
            message = 'Deleted {0} for {1}.'.format(entry.activity.name, entry.project)
            messages.info(request, message)
            url = request.GET.get('next', reverse('dashboard'))
            return HttpResponseRedirect(url)
        else:
            message = 'You are not authorized to delete this entry!'
            messages.error(request, message)

    return render(request, 'timepiece/entry/delete.html', {
        'entry': entry,
    })


class ScheduleMixin(object):

    def dispatch(self, request, *args, **kwargs):
        # Since we use get param in multiple places, attach it to the class
        default_week = utils.get_week_start(datetime.date.today()).date()

        if request.method == 'GET':
            week_start_str = request.GET.get('week_start', '')
        else:
            week_start_str = request.POST.get('week_start', '')

        # Account for an empty string
        self.week_start = default_week if week_start_str == '' \
            else utils.get_week_start(datetime.datetime.strptime(
                week_start_str, '%Y-%m-%d').date())

        return super(ScheduleMixin, self).dispatch(request, *args, **kwargs)

    def get_hours_for_week(self, week_start=None):
        """
        Gets all ProjectHours entries in the 7-day period beginning on
        week_start.
        """
        week_start = week_start if week_start else self.week_start
        week_end = week_start + relativedelta(days=7)

        return ProjectHours.objects.filter(
            week_start__gte=week_start, week_start__lt=week_end)


class ScheduleView(ScheduleMixin, TemplateView):
    template_name = 'timepiece/schedule/view.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('entries.can_clock_in'):
            return HttpResponseRedirect(reverse('auth_login'))

        return super(ScheduleView, self).dispatch(request, *args, **kwargs)

    def get_users_from_project_hours(self, project_hours):
        """
        Gets a list of the distinct users included in the project hours
        entries, ordered by name.
        """
        name = ('user__first_name', 'user__last_name')
        users = project_hours.values_list('user__id', *name).distinct()\
                             .order_by(*name)
        return users

    def get_context_data(self, **kwargs):
        context = super(ScheduleView, self).get_context_data(**kwargs)

        initial = {'week_start': self.week_start}
        form = ProjectHoursSearchForm(initial=initial)

        project_hours = self.get_hours_for_week()
        project_hours = project_hours.values(
            'project__id', 'project__name', 'user__id', 'user__first_name',
            'user__last_name', 'hours', 'published')
        project_hours = project_hours.order_by(
            '-project__type__billable', 'project__name')
        if not self.request.user.has_perm('entries.add_projecthours'):
            project_hours = project_hours.filter(published=True)
        users = self.get_users_from_project_hours(project_hours)
        id_list = [user[0] for user in users]
        projects = []

        func = lambda o: o['project__id']
        for project, entries in groupby(project_hours, func):
            entries = list(entries)
            proj_id = entries[0]['project__id']
            name = entries[0]['project__name']
            row = [{} for i in range(len(id_list))]
            for entry in entries:
                index = id_list.index(entry['user__id'])
                hours = entry['hours']
                row[index]['hours'] = row[index].get('hours', 0) + hours
                row[index]['published'] = entry['published']
            projects.append((proj_id, name, row))

        context.update({
            'form': form,
            'week': self.week_start,
            'prev_week': self.week_start - relativedelta(days=7),
            'next_week': self.week_start + relativedelta(days=7),
            'users': users,
            'project_hours': project_hours,
            'projects': projects
        })
        return context


class EditScheduleView(ScheduleMixin, TemplateView):
    template_name = 'timepiece/schedule/edit.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('entries.add_projecthours'):
            return HttpResponseRedirect(reverse('view_schedule'))

        return super(EditScheduleView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(EditScheduleView, self).get_context_data(**kwargs)

        form = ProjectHoursSearchForm(initial={
            'week_start': self.week_start
        })

        context.update({
            'form': form,
            'week': self.week_start,
            'ajax_url': reverse('ajax_schedule')
        })
        return context

    def post(self, request, *args, **kwargs):
        ph = self.get_hours_for_week(self.week_start).filter(published=False)

        if ph.exists():
            ph.update(published=True)
            msg = 'Unpublished project hours are now published'
        else:
            msg = 'There were no hours to publish'

        messages.info(request, msg)

        param = {
            'week_start': self.week_start.strftime(DATE_FORM_FORMAT)
        }
        url = '?'.join((reverse('edit_schedule'), urlencode(param),))

        return HttpResponseRedirect(url)


@cbv_decorator(permission_required('entries.add_projecthours'))
class ScheduleAjaxView(ScheduleMixin, View):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('entries.add_projecthours'):
            return HttpResponseRedirect(reverse('auth_login'))

        return super(ScheduleAjaxView, self).dispatch(request, *args, **kwargs)

    def get_instance(self, data, week_start):
        try:
            user = User.objects.get(pk=data.get('user', None))
            project = Project.objects.get(pk=data.get('project', None))
            hours = data.get('hours', None)
            week = datetime.datetime.strptime(week_start, DATE_FORM_FORMAT).date()

            ph = ProjectHours.objects.get(user=user, project=project, week_start=week)
            ph.hours = Decimal(hours)
        except (exceptions.ObjectDoesNotExist):
            ph = None

        return ph

    def get(self, request, *args, **kwargs):
        """
        Returns the data as a JSON object made up of the following key/value
        pairs:
            project_hours: the current project hours for the week
            projects: the projects that have hours for the week
            all_projects: all of the projects; used for autocomplete
            all_users: all users that can clock in; used for completion
        """
        perm = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename='can_clock_in'
        )
        project_hours = self.get_hours_for_week()
        project_hours = project_hours.values(
            'id', 'user', 'user__first_name', 'user__last_name',
            'project', 'hours', 'published')
        project_hours = project_hours.order_by(
            '-project__type__billable', 'project__name',
            'user__first_name', 'user__last_name')
        inner_qs = project_hours.values_list('project', flat=True)
        projects = Project.objects.filter(pk__in=inner_qs).values() \
            .order_by('name')
        all_projects = Project.objects.values('id', 'name')
        user_q = Q(groups__permissions=perm) | Q(user_permissions=perm)
        user_q |= Q(is_superuser=True)
        all_users = User.objects.filter(user_q) \
            .values('id', 'first_name', 'last_name')

        data = {
            'project_hours': list(project_hours),
            'projects': list(projects),
            'all_projects': list(all_projects),
            'all_users': list(all_users),
            'ajax_url': reverse('ajax_schedule'),
        }
        return HttpResponse(json.dumps(data, cls=DecimalEncoder),
                            content_type='application/json')

    def duplicate_entries(self, duplicate, week_update):
        def duplicate_builder(queryset, new_date):
            for instance in queryset:
                duplicate = deepcopy(instance)
                duplicate.id = None
                duplicate.published = False
                duplicate.week_start = new_date
                yield duplicate

        def duplicate_helper(queryset, new_date):
            try:
                ProjectHours.objects.bulk_create(
                    duplicate_builder(queryset, new_date)
                )
            except AttributeError:
                for entry in duplicate_builder(queryset, new_date):
                    entry.save()
            msg = 'Project hours were copied'
            messages.info(self.request, msg)

        this_week = datetime.datetime.strptime(week_update, DATE_FORM_FORMAT).date()
        prev_week = this_week - relativedelta(days=7)
        prev_week_qs = self.get_hours_for_week(prev_week)
        this_week_qs = self.get_hours_for_week(this_week)

        param = {
            'week_start': week_update
        }
        url = '?'.join((reverse('edit_schedule'), urlencode(param),))

        if not prev_week_qs.exists():
            msg = 'There are no hours to copy'
            messages.warning(self.request, msg)
        else:
            this_week_qs.delete()
            duplicate_helper(prev_week_qs, this_week)
        return HttpResponseRedirect(url)

    def update_week(self, week_start):
        try:
            instance = self.get_instance(self.request.POST, week_start)
        except TypeError:
            msg = 'Parameter week_start must be a date in the format ' \
                'yyyy-mm-dd'
            return HttpResponse(msg, status=500)

        form = ProjectHoursForm(self.request.POST, instance=instance)

        if form.is_valid():
            ph = form.save()
            return HttpResponse(str(ph.pk), content_type='text/plain')

        msg = 'The request must contain values for user, project, and hours'
        return HttpResponse(msg, status=500)

    def post(self, request, *args, **kwargs):
        """
        Create or update an hour entry for a particular use and project. This
        function expects the following values:
            user: the user pk for the hours
            project: the project pk for the hours
            hours: the actual hours to store
            week_start: the start of the week for the hours

        If the duplicate key is present along with week_update, then items
        will be duplicated from week_update to the current week
        """
        duplicate = request.POST.get('duplicate', None)
        week_update = request.POST.get('week_update', None)
        week_start = request.POST.get('week_start', None)

        if duplicate and week_update:
            return self.duplicate_entries(duplicate, week_update)

        return self.update_week(week_start)


@cbv_decorator(permission_required('entries.add_projecthours'))
class ScheduleDetailView(ScheduleMixin, View):

    def delete(self, request, *args, **kwargs):
        """Remove a project from the database."""
        assignment_id = kwargs.get('assignment_id', None)

        if assignment_id:
            ProjectHours.objects.filter(pk=assignment_id).delete()
            return HttpResponse('ok', content_type='text/plain')

        return HttpResponse('', status=500)
