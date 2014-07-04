from copy import deepcopy
import datetime, calendar
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from itertools import groupby
import json
import urllib

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
from timepiece.entries.forms import ClockInForm, ClockOutForm, \
        AddUpdateEntryForm, ProjectHoursForm, ProjectHoursSearchForm
from timepiece.entries.models import Entry, ProjectHours, Location, Activity

import pprint
pp = pprint.PrettyPrinter(indent=4)
import sys, traceback

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
        if 'period_start' in self.request.GET:
            param = self.request.GET.get('week_start')
            try:
                day = datetime.datetime.strptime(param, '%Y-%m-%d').date()
            except:
                pass
        period_start = utils.get_period_start(day)
        period_end = utils.get_period_end(period_start)
        return today, period_start, period_end

    def get_hours_per_week(self, user=None):
        """Retrieves the number of hours the user should work per week."""
        try:
            profile = UserProfile.objects.get(user=user or self.user)
        except UserProfile.DoesNotExist:
            profile = None
        return profile.hours_per_week if profile else Decimal('40.00')

    def get_hours_per_period(self, user=None):
        """Retrieves the number of hours the user should work per period."""
        today, period_start, period_end = self.get_dates()
        weekdays = utils.get_weekdays_count(period_start, period_end)
        return Decimal(weekdays * 8)

    def get_context_data(self, *args, **kwargs):
        today, period_start, period_end = self.get_dates()

        # Query for the user's active entry if it exists.
        active_entry = utils.get_active_entry(self.user)

        # Process this period's entries to determine assignment progress.
        period_entries = Entry.objects.filter(
            user=self.user,
            start_time__gte=period_start,
            end_time__lte=period_end) \
                .select_related('project')
        assignments = ProjectHours.objects.filter(user=self.user,
                week_start=period_start.date())
        project_progress = self.process_progress(period_entries, assignments)

        # Total hours that the user is expected to clock this period.
        total_assigned = self.get_hours_per_period(self.user)
        total_worked = sum([p['worked'] for p in project_progress])

        # Others' active entries.
        others_active_entries = Entry.objects.filter(end_time__isnull=True) \
                .exclude(user=self.user).select_related('user', 'project',
                'activity')

        return {
            'active_tab': self.active_tab,
            'today': today,
            'period_start': period_start.date(),
            'period_end': period_end.date(),
            'active_entry': active_entry,
            'total_assigned': total_assigned,
            'total_worked': total_worked,
            'project_progress': project_progress,
            'period_entries': period_entries,
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
@transaction.commit_on_success
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
        if not entry or not (entry.is_editable or
                request.user.has_perm('entries.view_payroll_summary')):
            raise Http404
    else:
        entry = None

    entry_user = entry.user if entry else request.user
    if request.method == 'POST':
        form = AddUpdateEntryForm(data=request.POST, instance=entry,
                user=entry_user)
        if form.is_valid():
            entry = form.save()
            if entry_id:
                message = 'The entry has been updated successfully.'
            else:
                message = 'The entry has been created successfully.'
            messages.info(request, message)
            url = request.REQUEST.get('next', reverse('dashboard'))
            return HttpResponseRedirect(url)
        else:
            message = 'Please fix the errors below.'
            messages.error(request, message)
    else:
        initial = dict([(k, request.GET[k]) for k in request.GET.keys()])
        form = AddUpdateEntryForm(instance=entry, user=entry_user,
                initial=initial)

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
    return_url = request.REQUEST.get('next', reverse('dashboard'))
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
        'next': request.REQUEST.get('next'),
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
        url = request.REQUEST.get('next', reverse('dashboard'))
        return HttpResponseRedirect(url)

    if request.method == 'POST':
        key = request.POST.get('key', None)
        if key and key == entry.delete_key:
            entry.delete()
            message = 'Deleted {0} for {1}.'.format(entry.activity.name,
                    entry.project)
            messages.info(request, message)
            url = request.REQUEST.get('next', reverse('dashboard'))
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
        default_period = utils.get_period_start(datetime.date.today()).date()

        if request.method == 'GET':
            period_start_str = request.GET.get('week_start', '')
        else:
            period_start_str = request.POST.get('week_start', '')
        self.user = request.user
        self.day = datetime.date.today() if period_start_str == '' \
            else datetime.datetime.strptime(
                period_start_str, '%Y-%m-%d').date()
        # Account for an empty string
        self.period_start = default_period if period_start_str == '' \
            else utils.get_period_start(datetime.datetime.strptime(
                period_start_str, '%Y-%m-%d').date())
        self.period_end = utils.get_period_end(self.period_start)
        self.period_hours = utils.get_weekdays_count(
            datetime.datetime.combine(self.period_start, 
                datetime.datetime.min.time()), self.period_end) * 8

        return super(ScheduleMixin, self).dispatch(request, *args,
                **kwargs)

    def get_hours_for_period(self, period_start=None):
        """
        Gets all ProjectHours entries in the 7-day period beginning on
        period_start.
        """
        period_start = period_start if period_start else self.period_start
        period_end = utils.get_period_end(period_start)

        return ProjectHours.objects.filter(
            week_start__gte=period_start, week_start__lt=period_end)

    def get_charges_for_period(self, period_start=None):
        """
        Gets all Entries in the 7-day period beginning on period_start.
        """
        period_start = period_start if period_start else self.period_start
        period_end = utils.get_period_end(period_start)

        return Entry.objects.filter(
            start_time__gte=period_start, end_time__lt=period_end,
            user=self.user)

    def get_charges_for_day(self, day=None):
        """
        Gets all Entries in the 7-day period beginning on period_start.
        """
        try:
            day = day or self.day
            period_start = datetime.datetime.combine(day, 
                datetime.datetime.min.time())
            period_end = datetime.datetime.combine(day, 
                datetime.datetime.max.time())

            return Entry.objects.filter(
                start_time__gte=period_start, end_time__lte=period_end,
                user=self.user)
        except:
            return []


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

        initial = {'period_start': self.period_start}
        form = ProjectHoursSearchForm(initial=initial)

        project_hours = self.get_hours_for_period()
        project_hours = project_hours.values('project__id', 'project__name',
                'user__id', 'user__first_name', 'user__last_name', 'hours',
                'published')
        project_hours = project_hours.order_by('-project__type__billable',
                'project__name')
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
            'period': self.period_start,
            'period_hours': self.period_hours,
            'prev_period': self.period_start - relativedelta(days=15),
            'next_period': self.period_start + relativedelta(days=15),
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

        return super(EditScheduleView, self).dispatch(request, *args,
                **kwargs)

    def get_context_data(self, **kwargs):
        context = super(EditScheduleView, self).get_context_data(**kwargs)

        form = ProjectHoursSearchForm(initial={
            'period_start': self.period_start
        })

        context.update({
            'form': form,
            'period_hours': self.period_hours,
            'period': self.period_start,
            'ajax_url': reverse('ajax_schedule')
        })
        return context

    def post(self, request, *args, **kwargs):
        ph = self.get_hours_for_period(self.period_start).filter(published=False)

        if ph.exists():
            ph.update(published=True)
            msg = 'Unpublished project hours are now published'
        else:
            msg = 'There were no hours to publish'

        messages.info(request, msg)

        param = {
            'period_start': self.period_start.strftime(DATE_FORM_FORMAT)
        }
        url = '?'.join((reverse('edit_schedule'), urllib.urlencode(param),))

        return HttpResponseRedirect(url)


@cbv_decorator(permission_required('entries.add_projecthours'))
class ScheduleAjaxView(ScheduleMixin, View):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('entries.add_projecthours'):
            return HttpResponseRedirect(reverse('auth_login'))

        return super(ScheduleAjaxView, self).dispatch(request, *args,
                **kwargs)

    def get_instance(self, data, period_start):
        try:
            user = User.objects.get(pk=data.get('user', None))
            project = Project.objects.get(pk=data.get('project', None))
            hours = data.get('hours', None)
            period = datetime.datetime.strptime(period_start,
                    DATE_FORM_FORMAT).date()

            ph = ProjectHours.objects.get(user=user, project=project,
                    week_start=period)
            ph.hours = Decimal(hours)
        except (exceptions.ObjectDoesNotExist):
            ph = None

        return ph

    def get(self, request, *args, **kwargs):
        """
        Returns the data as a JSON object made up of the following key/value
        pairs:
            project_hours: the current project hours for the period
            projects: the projects that have hours for the period
            all_projects: all of the projects; used for autocomplete
            all_users: all users that can clock in; used for completion
        """
        perm = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename='can_clock_in'
        )
        project_hours = self.get_hours_for_period().values(
            'id', 'user', 'user__first_name', 'user__last_name',
            'project', 'hours', 'published'
        ).order_by('-project__type__billable', 'project__name',
            'user__first_name', 'user__last_name')
        inner_qs = project_hours.values_list('project', flat=True)
        projects = Project.objects.filter(pk__in=inner_qs).values() \
            .order_by('name')
        all_projects = Project.objects.values('id', 'name')
        user_q = Q(groups__permissions=perm) | Q(user_permissions=perm)
        user_q |= Q(is_superuser=True)
        all_users = User.objects.filter(user_q) \
            .values('id', 'first_name', 'last_name')

        minder_for_projects = {}
        user_other_hours = {}
        try:
            # get projects the user is a minder for with all assigned users
            minder_for_projects = {}
            listed_users = []
            listed_projects = []
            for p in Project.objects.filter(point_person=request.user.id):
                user_ids = [u['id'] for u in p.users.values()]
                minder_for_projects[p.id] = user_ids
                listed_projects.append(p.id)
                listed_users.extend(user_ids)

            for ph in project_hours:
                listed_projects.append(ph['project'])
                listed_users.append(ph['user'])

            listed_users = list(set(listed_users))
            listed_projects = list(set(listed_projects))

            user_other_hours = {}
            for u_id in listed_users:
                user_other_hours[u_id] = 0
                user = User.objects.get(id=u_id)
                for ph in ProjectHours.objects.filter(
                            user=user,
                            week_start__gte=self.period_start,
                            week_start__lt=utils.get_period_end(self.period_start)):
                    if ph.project.id not in listed_projects:
                        user_other_hours[u_id] += ph.hours
        except:
            print sys.exc_info(), traceback.format_exc()

        data = {
            'project_hours': list(project_hours),
            'projects': list(projects),
            'all_projects': list(all_projects),
            'minder_for_projects': minder_for_projects,
            'user_other_hours': user_other_hours,
            'all_users': list(all_users),
            'ajax_url': reverse('ajax_schedule'),
        }
        return HttpResponse(json.dumps(data, cls=DecimalEncoder),
            mimetype='application/json')

    def duplicate_entries(self, duplicate, period_update):
        def duplicate_builder(queryset, new_date):
            for instance in queryset:
                duplicate = deepcopy(instance)
                duplicate.id = None
                duplicate.published = False
                duplicate.period_start = new_date
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

        this_period = datetime.datetime.strptime(period_update,
                DATE_FORM_FORMAT).date()
        if this_period.day == 1:
            prev_period = this_period - relativedelta(months=1)
            prev_period = prev_period.replace(day=15)
        else:
            prev_period = this_period.replace(day=1)

        prev_period_qs = self.get_hours_for_period(prev_period)
        this_period_qs = self.get_hours_for_period(this_period)

        param = {
            'period_start': period_update
        }
        url = '?'.join((reverse('edit_schedule'),
            urllib.urlencode(param),))

        if not prev_period_qs.exists():
            msg = 'There are no hours to copy'
            messages.warning(self.request, msg)
        else:
            this_period_qs.delete()
            duplicate_helper(prev_period_qs, this_period)
        return HttpResponseRedirect(url)

    def update_period(self, period_start):
        try:
            instance = self.get_instance(self.request.POST, period_start)
        except TypeError:
            msg = 'Parameter period_start must be a date in the format ' \
                'yyyy-mm-dd'
            return HttpResponse(msg, status=500)

        form = ProjectHoursForm(self.request.POST, instance=instance)

        if form.is_valid():
            ph = form.save()
            return HttpResponse(str(ph.pk), mimetype='text/plain')

        msg = 'The request must contain values for user, project, and hours'
        return HttpResponse(msg, status=500)

    def post(self, request, *args, **kwargs):
        """
        Create or update an hour entry for a particular use and project. This
        function expects the following values:
            user: the user pk for the hours
            project: the project pk for the hours
            hours: the actual hours to store
            period_start: the start of the period for the hours

        If the duplicate key is present along with period_update, then items
        will be duplicated from period_update to the current period
        """
        duplicate = request.POST.get('duplicate', None)
        period_update = request.POST.get('week_update', None)
        period_start = request.POST.get('week_start', None)

        if duplicate and period_update:
            return self.duplicate_entries(duplicate, period_update)

        return self.update_period(period_start)


@cbv_decorator(permission_required('entries.add_projecthours'))
class ScheduleDetailView(ScheduleMixin, View):

    def delete(self, request, *args, **kwargs):
        """Remove a project from the database."""
        assignment_id = kwargs.get('assignment_id', None)

        if assignment_id:
            ProjectHours.objects.filter(pk=assignment_id).delete()
            return HttpResponse('ok', mimetype='text/plain')

        return HttpResponse('', status=500)


class BulkEntryView(ScheduleMixin, TemplateView):
    template_name = 'timepiece/entry/bulk.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('entries.change_entry'):
            return HttpResponseRedirect(reverse('view_schedule'))

        return super(BulkEntryView, self).dispatch(request, *args,
                **kwargs)

    def get_context_data(self, **kwargs):
        context = super(BulkEntryView, self).get_context_data(**kwargs)

        form = ProjectHoursSearchForm(initial={
            'period_start': self.day
        })

        context.update({
            'form': form,
            'period': self.day,
            'period_hours': self.period_hours,
            'ajax_url': reverse('ajax_bulk_entry')
        })
        return context

    def post(self, request, *args, **kwargs):
        ph = self.get_charges_for_period(
            self.period_start).filter(published=False)

        if ph.exists():
            msg = 'Unpublished project hours are now published'
        else:
            msg = 'There were no hours to publish'

        messages.info(request, msg)

        param = {
            'period_start': self.period_start.strftime(DATE_FORM_FORMAT)
        }
        url = '?'.join((reverse('edit_schedule'), urllib.urlencode(param),))

        return HttpResponseRedirect(url)

@cbv_decorator(permission_required('entries.create_edit_entry'))
class BulkEntryAjaxView(ScheduleMixin, View):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('entries.create_edit_entry'):
            return HttpResponseRedirect(reverse('auth_login'))

        return super(BulkEntryAjaxView, self).dispatch(request, *args,
                **kwargs)

    def get_instance(self, data):
        try:
            entry = Entry.objects.get(id=data.get('entry_id'))
            # check somethings about the entry
            if entry.user.id != int(data.get('user')):
                raise exceptions.ObjectDoesNotExist
            if entry.project.id != int(data.get('project')):
                raise exceptions.ObjectDoesNotExist
            # TODO: add check on start_time being in correct period
            # period = datetime.datetime.strptime(period_start,
            #         DATE_FORM_FORMAT)
            # period_end = utils.get_period_end(period)
            # entries = Entry.objects.filter(user=user, project=project,
            #     start_time__gte=period, start_time__lte=period_end)

        except (exceptions.ObjectDoesNotExist):
            entry = None

        return entry

    def get(self, request, *args, **kwargs):
        """
        Returns the data as a JSON object made up of the following key/value
        pairs:
            charged_hours: the current total number of hours charged per project
            projects: the projects that have charged hours for the period
            all_projects: all of the projects; used for autocomplete
            period_dates: all dates in the period
        """
        
        perm = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Entry),
            codename='can_clock_in'
        )
        charged_hours = self.get_charges_for_day().values(
            'id', 'user', 'user__first_name', 'user__last_name', 'comments',
            'project', 'start_time', 'end_time', 'location', 'activity'
        ).order_by('-project__type__billable', 'project__name',
            'user__first_name', 'user__last_name', '-start_time')
        inner_qs = charged_hours.values_list('project', flat=True)
        projects = Project.objects.filter(pk__in=inner_qs).values() \
            .order_by('name')
        all_projects = Project.objects.values('id', 'name')
        all_activities = Activity.objects.values('id', 'name', 'code')
        all_locations = Location.objects.values('id', 'name')
        user_q = Q(groups__permissions=perm) | Q(user_permissions=perm)
        user_q |= Q(is_superuser=True)
        
        # further process charged_hours to get exactly what we want
        for ch in charged_hours:
            ch['total_hours'] = Entry.objects.get(id=ch['id']).total_hours
            ch['start_time'] = ch['start_time'].isoformat()
            ch['end_time'] =  ch['end_time'].isoformat()

        data = {
            'charged_hours': list(charged_hours),
            'projects': list(projects),
            'all_projects': list(all_projects),
            'all_activities': list(all_activities),
            'all_locations': list(all_locations),
            'period_dates': utils.get_period_dates(self.day),
            'ajax_url': reverse('ajax_bulk_entry'),
        }
        
        return HttpResponse(json.dumps(data, cls=DecimalEncoder),
            mimetype='application/json')

    def update_charges(self, period_start):
        try:
            print 'update charges'
            print 'data'
            print 'project', self.request.POST.get('project')
            print 'activity', self.request.POST.get('activity')
            print 'location', self.request.POST.get('location')
            entry = self.get_instance(self.request.POST)
            p = Project.objects.get(
                    id=int(self.request.POST.get('project')))
            a = Activity.objects.get(
                    id=int(self.request.POST.get('activity')))
            l = Location.objects.get(
                    id=int(self.request.POST.get('location')))
            print 'is entry?', entry, entry is not None
            if entry is not None:
                print 'entry times', entry.start_time, entry.end_time
                entries = Entry.objects.filter(
                    start_time__startswith=entry.start_time.date(),
                    project=entry.project,
                    user=entry.user).order_by('start_time')
                for e in entries:
                    if e.id != entry.id:
                        print 'deleting other entry'
                        e.delete()
            else:
                print 'date?', self.request.POST.get('date')
                pp.pprint(self.request.POST)
                date = datetime.datetime.strptime(
                    self.request.POST.get('date'), DATE_FORM_FORMAT).date()
                start = datetime.datetime.combine(date, 
                    datetime.datetime.min.time())
                entry = Entry(user=self.request.user,
                              project=p,
                              activity=a, # change to settings
                              location=l, # change to settings
                              start_time=start)
                entry.save()

        except TypeError:
            print sys.exc_info(), traceback.format_exc()
            msg = 'Parameter period_start must be a date in the format ' \
                'yyyy-mm-dd'
            return HttpResponse(msg, status=500)
        except:
            print sys.exc_info(), traceback.format_exc()

        try:
            duration = round(float(self.request.POST.get('duration'))*4.) / 4.
            entry.end_time = entry.start_time + relativedelta(hours=duration)
            # if using bulk entry, we are going to drop the seconds paused
            entry.seconds_paused = 0
            entry.comments = self.request.POST.get('comment', '')
            entry.project = p
            entry.location = l
            entry.activity = a
            entry.save()
            print 'entry times', entry.start_time, entry.end_time
            data = {'id': entry.id,
                    'user': entry.user.id,
                    'start_time': entry.start_time.isoformat(),
                    'end_time': entry.end_time.isoformat(),
                    'activity': entry.activity.id,
                    'location': entry.location.id,
                    'comment': entry.comments}
            return HttpResponse(json.dumps(data), status=200, mimetype='application/json')
        except:
            msg = 'The request must contain values for user, project, and hours'
            return HttpResponse(msg, status=500)

    def post(self, request, *args, **kwargs):
        """
        Create or update an hour entry for a particular use and project. This
        function expects the following values:
            user: the user pk for the hours
            project: the project pk for the hours
            hours: the actual hours to store
            period_start: the start of the period for the hours

        If the duplicate key is present along with period_update, then items
        will be duplicated from period_update to the current period
        """
        print 'got to POST'
        duplicate = request.POST.get('duplicate', None)
        period_update = request.POST.get('week_update', None)
        period_start = request.POST.get('week_start', None)
        print 'POST', request.POST

        if duplicate and period_update:
            return self.duplicate_entries(duplicate, period_update)

        return self.update_charges(period_start)
