from copy import deepcopy
import datetime, calendar
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
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View

from timepiece import utils
from timepiece.forms import DATE_FORM_FORMAT
from timepiece.utils.csv import DecimalEncoder
from timepiece.utils.views import cbv_decorator

from timepiece.crm.models import Project, UserProfile
from timepiece.entries.forms import ClockInForm, ClockOutForm, \
        AddUpdateEntryForm, ProjectHoursForm, ProjectHoursSearchForm, \
        WritedownEntryForm
from timepiece.entries.models import Entry, ProjectHours, Location, Activity

import pprint
pp = pprint.PrettyPrinter(indent=4)
import sys, traceback

class Dashboard(TemplateView):
    template_name = 'timepiece/dashboard.html'

    @method_decorator(login_required)
    def dispatch(self, request, active_tab, *args, **kwargs):
        if request.user.profile.business.id == 6:
            self.active_tab = active_tab or 'progress'
            self.user = request.user
            return super(Dashboard, self).dispatch(request, *args, **kwargs)
        else:
            return HttpResponseRedirect('/')

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
        # DO NOT INCLUDE WRITEDOWNS ON THE DASHBOARD
        period_entries = Entry.objects.filter(
            user=self.user, writedown=False,
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
        others_active_entries = Entry.objects.filter(end_time__isnull=True)
        others_active_entries = others_active_entries.exclude(user=self.user)
        others_active_entries = others_active_entries.select_related('user', 'project', 'activity')

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
            'period_end_display': (period_end + relativedelta(days=-1)).date()
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
            #hours = Decimal('%.2f' % (entry.get_total_seconds() / 3600.0))
            project_data[pk]['worked'] += entry.hours

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
        # added to check if entry is MANUAL or TIMECLOCK
        if abs(datetime.datetime.now()-entry.start_time).total_seconds() < 300.0:
            entry.mechanism = Entry.TIMECLOCK
            entry.save()
        message = 'You have clocked into {0} on {1}.'.format(
            entry.activity.name, entry.project)
        messages.info(request, message)
        return HttpResponseRedirect('/')

    ret_data = {
        'form': form,
        'active': active_entry,
    }
    try:
        ret_data['project'] = int(data.get('project', [0])[0])
    except:
        pass

    return render(request, 'timepiece/entry/clock_in.html', ret_data)


@permission_required('entries.can_clock_out')
def clock_out(request):
    entry = utils.get_active_entry(request.user)
    if not entry:
        message = "Not clocked in"
        messages.info(request, message)
        return HttpResponseRedirect('/')
    if request.POST:
        form = ClockOutForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save()
            # added to check if entry is MANUAL or TIMECLOCK
            if not(abs(datetime.datetime.now()-entry.end_time).total_seconds() < 300.0
                and entry.mechanism==Entry.TIMECLOCK):
                entry.mechanism = Entry.MANUAL
                entry.save()
            message = 'You have clocked out of {0} on {1}.'.format(
                entry.activity.name, entry.project)
            messages.info(request, message)
            return HttpResponseRedirect('/')
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
        form = AddUpdateEntryForm(data=request.POST, instance=entry,
                user=entry_user, acting_user=request.user)
        proj_id = request.POST.get('project', None)
        if proj_id:
            proj = Project.objects.get(id=int(proj_id))
            if proj.activity_group:
                form.fields['activity'].queryset = Activity.objects.filter(
                    id__in=[v['id'] for v in proj.activity_group.activities.values()])

        if form.is_valid():
            entry = form.save()
            # make sure that the mechanism is MANUAL rather than TIMECLOCK
            entry.mechanism = Entry.MANUAL
            entry.save()
            if entry_id:
                message = 'The entry has been updated successfully.'
            else:
                message = 'The entry has been created successfully.'
            messages.info(request, message)
            url = request.GET.get('next', '/')
            return HttpResponseRedirect(url)
        else:
            message = 'Please fix the errors below.'
            messages.error(request, message)
    else:
        initial = dict([(k, request.GET[k]) for k in request.GET.keys()])
        form = AddUpdateEntryForm(instance=entry,
                                  user=entry_user,
                                  initial=initial,
                                  acting_user=request.user)

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
        if request.user.has_perm('entries.view_payroll_summary'):
            try:
                entry = Entry.no_join.get(pk=entry_id, writedown=True)
            except:
                message = 'No such entry found.'
                messages.info(request, message)
                url = request.REQUEST.get('next', reverse('dashboard'))
                return HttpResponseRedirect(url)
        else:
            message = 'No such entry found.'
            messages.info(request, message)
            url = request.REQUEST.get('next', reverse('dashboard'))
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

def writedown_entry(request, orig_entry_id):
    """
    When a time entry, or part of a time entry, needs to be written-down
    this provide functionality to do that.  It requires that the amount
    (i.e. hours) being written-down are no more than the entry.
    Writedowns are only shown in certain parts of the front-end and reports.
    """
    try:
        orig_entry = Entry.no_join.get(pk=orig_entry_id)
    except Entry.DoesNotExist:
        message = 'No such entry found.'
        messages.info(request, message)
        url = request.REQUEST.get('next', reverse('dashboard'))
        return HttpResponseRedirect(url)

    if request.method == 'POST':
        form = WritedownEntryForm(orig_entry=orig_entry, data=request.POST)
        if form.is_valid():
            end_time = orig_entry.start_time + datetime.timedelta(
                hours=form.cleaned_data['hours'])
            entry = Entry(start_time=orig_entry.start_time,
                          end_time=end_time,
                          seconds_paused=0,
                          writedown=form.cleaned_data['writedown'],
                          comments=form.cleaned_data['comments'],
                          user=orig_entry.user,
                          writedown_user=request.user,
                          writedown_entry=orig_entry,
                          project=orig_entry.project,
                          activity=orig_entry.activity,
                          location=orig_entry.location,
                          entry_group=orig_entry.entry_group,
                          mechanism=Entry.WRITEDOWN,
                          status=Entry.APPROVED)
            entry.save()
            message = 'The writeoff has been successfully created.'
            messages.info(request, message)
            url = request.REQUEST.get('next', reverse('dashboard'))
            return HttpResponseRedirect(url)
        else:
            message = 'Please fix the errors below.'
            messages.error(request, message)

    else:
        initial = {'hours': float(orig_entry.hours) - orig_entry.written_down_hours,
                   'writedown': False,
                   'comments': 'This is a write down for %s %s\'s entry against Project %s starting at %s (Entry ID %d).' % (
                    orig_entry.user.first_name, orig_entry.user.last_name, orig_entry.project.code, orig_entry.start_time, orig_entry.id)}
        form = WritedownEntryForm(orig_entry=orig_entry, initial=initial)

    return render(request, 'timepiece/entry/writedown.html', {
        'orig_entry': orig_entry,
        'form': form,
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

        return super(ScheduleMixin, self).dispatch(request, *args, **kwargs)

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
        TODO: IGNORE WRITEDOWNS OR NOT? Currently writedown=False.
        """
        period_start = period_start if period_start else self.period_start
        period_end = utils.get_period_end(period_start)

        return Entry.objects.filter(
            start_time__gte=period_start, end_time__lt=period_end,
            user=self.user, writedown=False)

    def get_charges_for_day(self, day=None):
        """
        Gets all Entries in the 7-day period beginning on period_start.
        TODO: IGNORE WRITEDOWNS OR NOT? Currently writedown=False.
        """
        try:
            day = day or self.day
            period_start = datetime.datetime.combine(day,
                datetime.datetime.min.time())
            period_end = datetime.datetime.combine(day,
                datetime.datetime.max.time())

            return Entry.objects.filter(
                start_time__gte=period_start, end_time__lte=period_end,
                user=self.user, writedown=False)
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
            'prev_period': self.period_start - relativedelta(days=7),
            'next_period': self.period_start + relativedelta(days=7),
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
        url = '?'.join((reverse('edit_schedule'), urlencode(param),))

        return HttpResponseRedirect(url)


@cbv_decorator(permission_required('entries.add_projecthours'))
class ScheduleAjaxView(ScheduleMixin, View):

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('entries.add_projecthours'):
            return HttpResponseRedirect(reverse('auth_login'))

        return super(ScheduleAjaxView, self).dispatch(request, *args, **kwargs)

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
            'project', 'hours', 'published')
        project_hours = project_hours.order_by(
            'project__name',
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
                            content_type='application/json')

    def duplicate_entries(self, duplicate, period_update):
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

        this_period = datetime.datetime.strptime(period_update,
                DATE_FORM_FORMAT).date()
        prev_period = utils.get_period_start(this_period - relativedelta(days=1)).date()

        prev_period_qs = self.get_hours_for_period(prev_period)
        this_period_qs = self.get_hours_for_period(this_period)

        param = {
            'week_start': period_update
        }
        url = '?'.join((reverse('edit_schedule'), urlencode(param),))

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
            period_start: the start of the period for the hours

        If the duplicate key is present along with period_update, then items
        will be duplicated from period_update to the current period
        """
        duplicate = request.POST.get('duplicate', None)
        period_update = request.POST.get('period_update', None)
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
            return HttpResponse('ok', content_type='text/plain')

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
            .order_by('code')
        all_projects = Project.trackable.filter(users=request.user).values('id', 'code', 'name', 'activity_group__activities')
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
            'all_projects': list(all_projects) + list(Project.objects.filter(pk__in=inner_qs).values('id', 'code', 'name', 'activity_group__activities')),
            'all_activities': list(all_activities),
            'all_locations': list(all_locations),
            'period_dates': utils.get_period_dates(self.day),
            'ajax_url': reverse('ajax_bulk_entry'),
        }

        return HttpResponse(json.dumps(data, cls=DecimalEncoder),
            content_type='application/json')

    def update_charges(self, period_start):
        try:
            entry = self.get_instance(self.request.POST)
            p = Project.objects.get(
                    id=int(self.request.POST.get('project')))
            a = Activity.objects.get(
                    id=int(self.request.POST.get('activity')))
            l = Location.objects.get(
                    id=int(self.request.POST.get('location')))
            extra_duration = 0
            extra_comments = ''
            if entry is not None:
                pass
                # entries = Entry.objects.filter(
                #     start_time__startswith=entry.start_time.date(),
                #     project=entry.project,
                #     activity=entry.activity,
                #     location=entry.location,
                #     user=entry.user).order_by('start_time')
                # for e in entries:
                #     if e.id != entry.id:
                #         print 'deleting other entry'
                #         extra_duration += e.hours
                #         if e.comments.strip():
                #             extra_comments += ' -- ' + e.comments
                #         e.delete()
            else:
                date = datetime.datetime.strptime(
                    self.request.POST.get('date'), DATE_FORM_FORMAT).date()
                start = datetime.datetime.combine(date,
                    datetime.datetime.min.time())
                entry = Entry(user=self.request.user,
                              project=p,
                              activity=a, # change to settings
                              location=l, # change to settings
                              start_time=start,
                              mechanism=Entry.BULK)
                entry.clean()
                entry.save()

        except TypeError:
            print sys.exc_info(), traceback.format_exc()
            msg = 'Parameter period_start must be a date in the format ' \
                'yyyy-mm-dd'
            return HttpResponse(msg, status=500)
        except ValidationError:
            print sys.exc_info(), traceback.format_exc()
            return HttpResponse('Could not save entry: Validation Error.  You cannot add/edit hours after a timesheet has been approved.', status=500)
        except:
            return HttpResponse(msg, status=500)

        try:
            #duration = round(float(self.request.POST.get('duration'))*4.) / 4. + float(extra_duration) # round to quarter-hour
            duration = float(self.request.POST.get('duration')) + float(extra_duration)
            entry.end_time = entry.start_time + relativedelta(hours=duration)
            # if using bulk entry, we are going to drop the seconds paused
            entry.seconds_paused = 0
            entry.comments = self.request.POST.get('comment', '') + extra_comments
            entry.project = p
            entry.location = l
            entry.activity = a
            entry.mechanism = Entry.BULK
            entry.save()
            data = {'id': entry.id,
                    'user': entry.user.id,
                    'start_time': entry.start_time.isoformat(),
                    'end_time': entry.end_time.isoformat(),
                    'activity': entry.activity.id,
                    'location': entry.location.id,
                    'comment': entry.comments}
            return HttpResponse(json.dumps(data), status=200, content_type='application/json')
        except:
            print sys.exc_info(), traceback.format_exc()
            msg = 'The request must contain values for user, project, activity, location and hours'
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
            print 'ERROR: WE SHOULD NEVER GET HERE!!!'
            return self.duplicate_entries(duplicate, period_update)

        return self.update_charges(period_start)

def activity_cheat_sheet(request):
    return render(request, 'timepiece/entry/activity_cheat_sheet.html', {
        'activities': Activity.objects.all().order_by('name'),
    })

@login_required
def get_active_entry(request):
    active_entry = utils.get_active_entry(request.user)
    if active_entry:
        return JsonResponse(active_entry.to_json())
    else:
        return HttpResponse('')


def toggle_pause_entry(request):
    active_entry = utils.get_active_entry(request.user)
    active_entry.toggle_paused()
    active_entry.save()
    if active_entry:
        return JsonResponse(active_entry.to_json())
    else:
        return HttpResponse('')
