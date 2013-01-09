from copy import deepcopy
import csv
import datetime
import json
import urllib

from dateutil.relativedelta import relativedelta
from decimal import Decimal
from itertools import groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.core import exceptions
from django.core.urlresolvers import reverse, resolve
from django.db import transaction
from django.db.models import Sum, Q, Min, Max
from django.http import HttpResponse, HttpResponseRedirect
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import ListView, DetailView, View
from django.views.generic.base import TemplateView

try:
    from django.utils import timezone
except ImportError:
    from timepiece import timezone

from timepiece import forms as timepiece_forms
from timepiece import models as timepiece
from timepiece import utils
from timepiece.templatetags.timepiece_tags import seconds_to_hours
from timepiece.utils import DecimalEncoder


@login_required
def search(request):
    form = timepiece_forms.QuickSearchForm(request.GET or None)
    if form.is_valid():
        return HttpResponseRedirect(form.save())
    return render(request, 'timepiece/search_results.html', {
        'form': form,
    })


class CSVMixin(object):

    def render_to_response(self, context):
        response = HttpResponse(content_type='text/csv')
        fn = self.get_filename(context)
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % fn
        rows = self.convert_context_to_csv(context)
        writer = csv.writer(response)
        for row in rows:
            writer.writerow(row)
        return response

    def get_filename(self, context):
        raise NotImplemented('You must implement this in the subclass')

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file"""
        raise NotImplemented('You must implement this in the subclass')


@login_required
def dashboard(request, active_tab):
    active_tab = active_tab or 'progress'
    user = request.user
    Entry = timepiece.Entry
    ProjectHours = timepiece.ProjectHours

    today = datetime.date.today()
    day = today
    if 'week_start' in request.GET:
        param = request.GET.get('week_start')
        try:
            day = datetime.datetime.strptime(param, '%Y-%m-%d').date()
        except:
            pass
    week_start = utils.get_week_start(day)
    week_end = week_start + relativedelta(days=6)

    # Query for the user's active entry if it exists.
    active_entry = utils.get_active_entry(user)

    # Process this week's entries to determine assignment progress.
    week_entries = Entry.objects.filter(user=user) \
            .timespan(week_start, span='week', current=True) \
            .select_related('project')
    assignments = ProjectHours.objects.filter(user=user,
            week_start=week_start.date())
    project_progress = utils.process_progress(week_entries, assignments)

    # Total hours that the user is expected to clock this week.
    total_assigned = utils.get_hours_per_week(user)
    total_worked = sum([p['worked'] for p in project_progress])

    # Others' active entries.
    others_active_entries = Entry.objects.filter(end_time__isnull=True) \
            .exclude(user=user).select_related('user', 'project', 'activity')

    return render(request, 'timepiece/dashboard.html', {
        'active_tab': active_tab,
        'today': today,
        'week_start': week_start.date(),
        'week_end': week_end.date(),
        'active_entry': active_entry,
        'total_assigned': total_assigned,
        'total_worked': total_worked,
        'project_progress': project_progress,
        'week_entries': week_entries,
        'others_active_entries': others_active_entries,
    })


@permission_required('timepiece.can_clock_in')
@transaction.commit_on_success
def clock_in(request):
    """For clocking the user into a project."""
    user = request.user
    active_entry = utils.get_active_entry(user)

    initial = dict([(k, v) for k, v in request.GET.items()])
    form = timepiece_forms.ClockInForm(request.POST or None, initial=initial,
                                       user=user, active=active_entry)
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


@permission_required('timepiece.can_clock_out')
def clock_out(request):
    entry = utils.get_active_entry(request.user)
    if not entry:
        raise Http404
    if request.POST:
        form = timepiece_forms.ClockOutForm(request.POST, instance=entry)
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
        form = timepiece_forms.ClockOutForm(instance=entry)
    return render(request, 'timepiece/entry/clock_out.html', {
        'form': form,
        'entry': entry,
    })


@permission_required('timepiece.can_pause')
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


@permission_required('timepiece.change_entry')
def create_edit_entry(request, entry_id=None):
    if entry_id:
        try:
            entry = timepiece.Entry.no_join.get(pk=entry_id)
            if not (entry.is_editable or
                    request.user.has_perm('timepiece.view_payroll_summary')):
                raise Http404
        except timepiece.Entry.DoesNotExist:
            raise Http404
    else:
        entry = None

    if request.method == 'POST':
        form = timepiece_forms.AddUpdateEntryForm(
            request.POST,
            instance=entry,
            user=entry.user if entry else request.user,
        )
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
        form = timepiece_forms.AddUpdateEntryForm(
            instance=entry,
            user=request.user,
            initial=initial,
        )

    return render(request, 'timepiece/entry/create_edit.html', {
        'form': form,
        'entry': entry,
    })


@permission_required('timepiece.view_payroll_summary')
def reject_entry(request, entry_id):
    """
    Admins can reject an entry that has been verified or approved but not
    invoiced to set its status to 'unverified' for the user to fix.
    """
    return_url = request.REQUEST.get('next', reverse('dashboard'))
    try:
        entry = timepiece.Entry.no_join.get(pk=entry_id)
    except:
        message = 'No such log entry.'
        messages.error(request, message)
        return redirect(return_url)

    if entry.status == 'unverified' or entry.status == 'invoiced':
        msg_text = 'This entry is unverified or is already invoiced.'
        messages.error(request, msg_text)
        return redirect(return_url)

    if request.POST.get('Yes'):
        entry.status = 'unverified'
        entry.save()
        msg_text = 'The entry\'s status was set to unverified.'
        messages.info(request, msg_text)
        return redirect(return_url)
    return render(request, 'timepiece/entry/reject.html', {
        'entry': entry,
        'next': request.REQUEST.get('next'),
    })


@permission_required('timepiece.view_payroll_summary')
def reject_user_timesheet(request, user_id):
    """
    This allows admins to reject all entries, instead of just one
    """
    form = timepiece_forms.YearMonthForm(request.GET or request.POST)
    user = User.objects.get(pk=user_id)
    if form.is_valid():
        from_date, to_date = form.save()
        entries = timepiece.Entry.no_join.filter(status='verified', user=user,
            start_time__gte=from_date, end_time__lte=to_date)
        if request.POST.get('yes'):
            if entries.exists():
                count = entries.count()
                entries.update(status='unverified')
                msg = 'You have rejected %d previously verified entries.' \
                    % count
            else:
                msg = 'There are no verified entries to reject.'
            messages.info(request, msg)
        else:
            return render(request, 'timepiece/user/timesheet/reject.html', {
                'date': from_date,
                'timesheet_user': user
            })
    else:
        msg = 'You must provide a month and year for entries to be rejected.'
        messages.error(request, msg)

    url = reverse('view_user_timesheet', args=(user_id,))
    return HttpResponseRedirect(url)


@permission_required('timepiece.delete_entry')
def delete_entry(request, entry_id):
    """
    Give the user the ability to delete a log entry, with a confirmation
    beforehand.  If this method is invoked via a GET request, a form asking
    for a confirmation of intent will be presented to the user. If this method
    is invoked via a POST request, the entry will be deleted.
    """
    try:
        entry = timepiece.Entry.no_join.get(pk=entry_id, user=request.user)
    except timepiece.Entry.DoesNotExist:
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


class ProjectTimesheet(DetailView):
    template_name = 'timepiece/project/timesheet.html'
    model = timepiece.Project
    context_object_name = 'project'
    pk_url_kwarg = 'pk'  # This parameter was introduced in Django 1.4.
                         # When we drop support for Django 1.3, we can
                         # change this to project_id for consistency of the
                         # URL structure.

    @method_decorator(permission_required('timepiece.view_project_time_sheet'))
    def dispatch(self, *args, **kwargs):
        return super(ProjectTimesheet, self).dispatch(*args, **kwargs)

    def get(self, *args, **kwargs):
        if 'csv' in self.request.GET:
            request_get = self.request.GET.copy()
            request_get.pop('csv')
            return_url = reverse('view_project_timesheet_csv',
                                 args=(self.get_object().pk,))
            return_url += '?%s' % urllib.urlencode(request_get)
            return redirect(return_url)
        return super(ProjectTimesheet, self).get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ProjectTimesheet, self).get_context_data(**kwargs)
        project = self.object
        year_month_form = timepiece_forms.YearMonthForm(self.request.GET or
                                                        None)
        if self.request.GET and year_month_form.is_valid():
            from_date, to_date = year_month_form.save()
        else:
            date = utils.add_timezone(datetime.datetime.today())
            from_date = utils.get_month_start(date).date()
            to_date = from_date + relativedelta(months=1)
        entries_qs = timepiece.Entry.objects
        entries_qs = entries_qs.timespan(from_date, span='month').filter(
            project=project
        )
        extra_values = ('start_time', 'end_time', 'comments', 'seconds_paused',
                'id', 'location__name', 'project__name', 'activity__name',
                'status')
        month_entries = entries_qs.date_trunc('month', extra_values)
        total = entries_qs.aggregate(hours=Sum('hours'))['hours']
        user_entries = entries_qs.order_by().values(
            'user__first_name', 'user__last_name').annotate(
            sum=Sum('hours')).order_by('-sum'
        )
        activity_entries = entries_qs.order_by().values(
            'activity__name').annotate(
            sum=Sum('hours')).order_by('-sum'
        )
        context.update({
            'project': project,
            'year_month_form': year_month_form,
            'from_date': from_date,
            'to_date': to_date - datetime.timedelta(days=1),
            'entries': month_entries,
            'total': total,
            'user_entries': user_entries,
            'activity_entries': activity_entries,
        })
        return context


class ProjectTimesheetCSV(CSVMixin, ProjectTimesheet):

    def get_filename(self, context):
        project = self.object.name
        to_date_str = context['to_date'].strftime('%m-%d-%Y')
        return 'Project_timesheet {0} {1}'.format(project, to_date_str)

    def convert_context_to_csv(self, context):
        rows = []
        rows.append([
            'Date',
            'Person',
            'Activity',
            'Location',
            'Time In',
            'Time Out',
            'Breaks',
            'Hours',
        ])
        for entry in context['entries']:
            data = [
                entry['start_time'].strftime('%x'),
                entry['user__first_name'] + ' ' + entry['user__last_name'],
                entry['activity__name'],
                entry['location__name'],
                entry['start_time'].strftime('%X'),
                entry['end_time'].strftime('%X'),
                seconds_to_hours(entry['seconds_paused']),
                entry['hours'],
            ]
            rows.append(data)
        total = context['total']
        rows.append(('', '', '', '', '', '', 'Total:', total))
        return rows


@login_required
def view_user_timesheet(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if not (request.user.has_perm('timepiece.view_entry_summary') or \
        user.pk == request.user.pk):
        return HttpResponseForbidden('Forbidden')
    today_reset = utils.add_timezone(datetime.datetime.today())
    today_reset = today_reset.replace(hour=0, minute=0, second=0, \
        microsecond=0)
    from_date = utils.get_month_start(today_reset)
    to_date = from_date + relativedelta(months=1)
    can_view_summary = request.user and \
        request.user.has_perm('timepiece.view_entry_summary')
    form = timepiece_forms.UserYearMonthForm if can_view_summary else \
        timepiece_forms.YearMonthForm
    year_month_form = form(request.GET or None)
    if year_month_form.is_valid():
        if can_view_summary:
            from_date, to_date, form_user = year_month_form.save()
            is_update = request.GET.get('yearmonth', None)
            if form_user and is_update:
                url = reverse('view_user_timesheet', args=(form_user.pk,))
                # Do not use request.GET in urlencode in case it has the
                # yearmonth parameter (redirect loop otherwise)
                request_data = {
                    'month': from_date.month,
                    'year': from_date.year,
                    'user': form_user.pk
                }
                url += '?{0}'.format(urllib.urlencode(request_data))
                return HttpResponseRedirect(url)
        else:
            from_date, to_date = year_month_form.save()
    entries_qs = timepiece.Entry.objects.filter(user=user)
    month_qs = entries_qs.timespan(from_date, span='month')
    extra_values = ('start_time', 'end_time', 'comments', 'seconds_paused',
            'id', 'location__name', 'project__name', 'activity__name',
            'status')
    month_entries = month_qs.date_trunc('month', extra_values)
    # For grouped entries, back date up to the start of the week.
    first_week = utils.get_week_start(from_date)
    month_week = first_week + datetime.timedelta(weeks=1)
    grouped_qs = entries_qs.timespan(first_week, to_date=to_date)
    intersection = grouped_qs.filter(start_time__lt=month_week,
        start_time__gte=from_date)
    # If the month of the first week starts in the previous
    # month and we dont have entries in that previous ISO
    # week, then update the first week to start at the first
    # of the actual month
    if not intersection and first_week.month < from_date.month:
        grouped_qs = entries_qs.timespan(from_date, to_date=to_date)
    grouped_totals = utils.grouped_totals(grouped_qs) if month_entries else ''
    project_entries = month_qs.order_by().values(
        'project__name').annotate(sum=Sum('hours')).order_by('-sum')
    summary = timepiece.Entry.summary(user, from_date, to_date)
    show_approve = show_verify = False
    if request.user.has_perm('timepiece.change_entry') or \
        request.user.has_perm('timepiece.approve_timesheet') or \
        user == request.user:
        statuses = list(month_qs.values_list('status', flat=True))
        total_statuses = len(statuses)
        unverified_count = statuses.count('unverified')
        verified_count = statuses.count('verified')
        approved_count = statuses.count('approved')
    if request.user.has_perm('timepiece.change_entry') or user == request.user:
        show_verify = unverified_count != 0
    if request.user.has_perm('timepiece.approve_timesheet'):
        show_approve = verified_count + approved_count == total_statuses \
        and verified_count > 0 and total_statuses != 0
    return render(request, 'timepiece/user/timesheet/view.html', {
        'year_month_form': year_month_form,
        'from_date': from_date,
        'to_date': to_date - datetime.timedelta(days=1),
        'show_verify': show_verify,
        'show_approve': show_approve,
        'timesheet_user': user,
        'entries': month_entries,
        'grouped_totals': grouped_totals,
        'project_entries': project_entries,
        'summary': summary,
    })


@login_required
def change_user_timesheet(request, user_id, action):
    user = get_object_or_404(User, pk=user_id)
    admin_verify = request.user.has_perm('timepiece.view_entry_summary')
    perm = True

    if not admin_verify and action == 'verify' and user != request.user:
        perm = False
    if not admin_verify and action == 'approve':
        perm = False

    if not perm:
        return HttpResponseForbidden('Forbidden: You cannot {0} this ' \
            'timesheet.'.format(action))

    try:
        from_date = request.GET.get('from_date')
        from_date = utils.add_timezone(
            datetime.datetime.strptime(from_date, '%Y-%m-%d'))
    except (ValueError, OverflowError, KeyError):
        raise Http404
    to_date = from_date + relativedelta(months=1)
    entries = timepiece.Entry.no_join.filter(user=user_id,
                                             end_time__gte=from_date,
                                             end_time__lt=to_date)
    active_entries = timepiece.Entry.no_join.filter(
        user=user_id,
        start_time__lt=to_date,
        end_time=None,
        status='unverified'
    )
    filter_status = {
        'verify': 'unverified',
        'approve': 'verified',
    }
    entries = entries.filter(status=filter_status[action])

    return_url = reverse('view_user_timesheet', args=(user_id,))
    return_url += '?%s' % urllib.urlencode({
        'year': from_date.year,
        'month': from_date.month,
    })
    if active_entries:
        msg = 'You cannot verify/approve this timesheet while the user {0} ' \
            'has an active entry. Please have them close any active ' \
            'entries.'.format(user.get_full_name())
        messages.error(request, msg)
        return redirect(return_url)
    if request.POST.get('do_action') == 'Yes':
        update_status = {
            'verify': 'verified',
            'approve': 'approved',
        }
        entries.update(status=update_status[action])
        messages.info(request,
            'Your entries have been %s' % update_status[action])
        return redirect(return_url)
    hours = entries.all().aggregate(s=Sum('hours'))['s']
    if not hours:
        msg = 'You cannot verify/approve a timesheet with no hours'
        messages.error(request, msg)
        return redirect(return_url)
    return render(request, 'timepiece/user/timesheet/change.html', {
        'action': action,
        'timesheet_user': user,
        'from_date': from_date,
        'to_date': to_date - datetime.timedelta(days=1),
        'return_url': return_url,
        'hours': hours,
    })


@login_required
@transaction.commit_on_success
def create_invoice(request):
    pk = request.GET.get('project', None)
    to_date = request.GET.get('to_date', None)
    if not (pk and to_date):
        raise Http404
    from_date = request.GET.get('from_date', None)
    if not request.user.has_perm('timepiece.generate_project_invoice'):
        return HttpResponseForbidden('Forbidden')
    try:
        to_date = utils.add_timezone(
            datetime.datetime.strptime(to_date, '%Y-%m-%d'))
        if from_date:
            from_date = utils.add_timezone(
                datetime.datetime.strptime(from_date, '%Y-%m-%d'))
    except (ValueError, OverflowError):
        raise Http404
    project = get_object_or_404(timepiece.Project, pk=pk)
    initial = {
        'project': project,
        'user': request.user,
        'from_date': from_date,
        'to_date': to_date,
    }
    entries_query = {
        'status': 'approved',
        'end_time__lt': to_date + relativedelta(days=1),
        'project__id': project.id
    }
    if from_date:
        entries_query.update({'end_time__gte': from_date})
    invoice_form = timepiece_forms.InvoiceForm(request.POST or None,
                                               initial=initial)
    if request.POST and invoice_form.is_valid():
        invoice = invoice_form.save()
        entries = timepiece.Entry.no_join.filter(**entries_query)
        entries.update(status=invoice.status, entry_group=invoice)
        return HttpResponseRedirect(reverse('view_invoice', args=[invoice.pk]))
    else:
        entries = timepiece.Entry.objects.filter(**entries_query)
        entries = entries.order_by('start_time')
        if not entries:
            raise Http404
    return render(request, 'timepiece/invoice/create.html', {
        'invoice_form': invoice_form,
        'entries': entries.select_related(),
        'project': project,
        'totals': timepiece.HourGroup.objects.summaries(entries),
        'from_date': from_date,
        'to_date': to_date,
    })


@permission_required('timepiece.change_entrygroup')
def list_outstanding_invoices(request):
    from_date = None
    to_date = utils.get_month_start().date()
    defaults = {
        'to_date': (to_date - relativedelta(days=1)).strftime('%m/%d/%Y'),
    }
    date_form = timepiece_forms.DateForm(request.GET or defaults)
    if request.GET and date_form.is_valid():
        from_date, to_date = date_form.save()

    datesQ = Q()
    datesQ &= Q(end_time__gte=from_date) if from_date else Q()
    datesQ &= Q(end_time__lt=to_date) if to_date else Q()
    billableQ = Q(project__type__billable=True, project__status__billable=True)
    statusQ = Q(status='approved')
    ordering = ('project__type__label', 'project__status__label',
            'project__business__name', 'project__name', 'status')

    entries = timepiece.Entry.objects.filter(datesQ, billableQ, statusQ)
    project_totals = entries.order_by(*ordering)

    return render(request, 'timepiece/invoice/outstanding.html', {
        'date_form': date_form,
        'project_totals': project_totals if to_date else [],
        'to_date': to_date - relativedelta(days=1) if to_date else '',
        'from_date': from_date,
    })


def list_invoices(request):
    search_form = timepiece_forms.SearchForm(request.GET)
    query = Q()
    if search_form.is_valid():
        search = search_form.save()
        query |= Q(
            Q(user__username__icontains=search) |
            Q(project__name__icontains=search) |
            Q(comments__icontains=search) |
            Q(number__icontains=search)
        )
    invoices = timepiece.EntryGroup.objects.filter(query).order_by('-created')
    return render(request, 'timepiece/invoice/list.html', {
        'invoices': invoices,
        'search_form': search_form,
    })


class InvoiceDetail(DetailView):
    template_name = 'timepiece/invoice/view.html'
    model = timepiece.EntryGroup
    context_object_name = 'invoice'
    pk_url_kwarg = 'pk'  # This parameter was introduced in Django 1.4.
                         # When we drop support for Django 1.3, we can
                         # change this to invoice_id for consistency of the
                         # URL structure.

    @method_decorator(permission_required('timepiece.change_entrygroup'))
    def dispatch(self, *args, **kwargs):
        return super(InvoiceDetail, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(InvoiceDetail, self).get_context_data(**kwargs)
        invoice = context['invoice']
        entries = invoice.entries.order_by('start_time').select_related()
        return {
            'invoice': invoice,
            'entries': entries,
            'totals': timepiece.HourGroup.objects.summaries(entries),
            'from_date': invoice.start,
            'to_date': invoice.end,
            'project': invoice.project,
        }


class InvoiceEntriesDetail(InvoiceDetail):
    template_name = 'timepiece/invoice/view_entries.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceEntriesDetail, self).get_context_data(**kwargs)
        entries = context['entries']
        context.update({
            'total': entries.aggregate(hours=Sum('hours'))['hours'],
        })
        return context


class InvoiceDetailCSV(CSVMixin, InvoiceDetail):

    def get_filename(self, context):
        invoice = context['invoice']
        project = str(invoice.project).replace(' ', '_')
        end_day = invoice.end.strftime('%m-%d-%Y')
        return 'Invoice-{0}-{1}'.format(project, end_day)

    def convert_context_to_csv(self, context):
        rows = []
        rows.append([
            'Date',
            'Weekday',
            'Name',
            'Location',
            'Time In',
            'Time Out',
            'Breaks',
            'Hours',
        ])
        for entry in context['entries']:
            data = [
                entry.start_time.strftime('%x'),
                entry.start_time.strftime('%A'),
                entry.user.get_full_name(),
                entry.location,
                entry.start_time.strftime('%X'),
                entry.end_time.strftime('%X'),
                seconds_to_hours(entry.seconds_paused),
                entry.hours,
            ]
            rows.append(data)
        total = context['entries'].aggregate(hours=Sum('hours'))['hours']
        rows.append(('', '', '', '', '', '', 'Total:', total))
        return rows


class InvoiceEdit(InvoiceDetail):
    template_name = 'timepiece/invoice/edit.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceEdit, self).get_context_data(**kwargs)
        invoice_form = timepiece_forms.InvoiceForm(instance=self.object)
        context.update({
            'invoice_form': invoice_form,
        })
        return context

    def post(self, request, **kwargs):
        invoice = get_object_or_404(timepiece.EntryGroup, pk=kwargs.get(self.pk_url_kwarg))
        self.object = invoice
        initial = {
            'project': invoice.project,
            'user': request.user,
            'from_date': invoice.start,
            'to_date': invoice.end,
        }
        invoice_form = timepiece_forms.InvoiceForm(request.POST,
                                                   initial=initial,
                                                   instance=invoice)
        if invoice_form.is_valid():
            invoice_form.save()
            return HttpResponseRedirect(reverse('view_invoice', kwargs=kwargs))
        else:
            context = super(InvoiceEdit, self).get_context_data(**kwargs)
            context.update({
                'invoice_form': invoice_form,
            })
            return self.render_to_response(context)


class InvoiceDelete(InvoiceDetail):
    template_name = 'timepiece/invoice/delete.html'

    def post(self, request, **kwargs):
        invoice = get_object_or_404(timepiece.EntryGroup, pk=kwargs.get(self.pk_url_kwarg))
        if 'delete' in request.POST:
            invoice.delete()
            return HttpResponseRedirect(reverse('list_invoices'))
        else:
            return redirect(reverse('edit_invoice', kwargs=kwargs))


@permission_required('timepiece.change_entrygroup')
def delete_invoice_entry(request, invoice_id, entry_id):
    invoice = get_object_or_404(timepiece.EntryGroup, pk=invoice_id)
    entry = get_object_or_404(timepiece.Entry, pk=entry_id)
    if request.POST:
        entry.status = 'approved'
        entry.entry_group = None
        entry.save()
        return HttpResponseRedirect(reverse('edit_invoice', args=(invoice_id,)))
    return render(request, 'timepiece/invoice/delete_entry.html', {
        'invoice': invoice,
        'entry': entry,
    })


@permission_required('timepiece.view_business')
def list_businesses(request):
    form = timepiece_forms.SearchForm(request.GET)
    businesses = timepiece.Business.objects.all()
    if form.is_valid() and 'search' in request.GET:
        search = form.cleaned_data['search']
        searchQ = Q(name__icontains=search) | Q(description__icontains=search)
        businesses = businesses.filter(searchQ)
        if businesses.count() == 1:
            url = request.REQUEST.get('next',
                    reverse('view_business', args=(businesses[0].pk,)))
            return HttpResponseRedirect(url)
    return render(request, 'timepiece/business/list.html', {
        'form': form,
        'businesses': businesses,
    })


@permission_required('timepiece.view_business')
def view_business(request, business_id):
    business = get_object_or_404(timepiece.Business, pk=business_id)
    return render(request, 'timepiece/business/view.html', {
        'business': business,
    })


@permission_required('timepiece.add_business')
def create_edit_business(request, business_id=None):
    business = get_object_or_404(timepiece.Business, pk=business_id) if business_id else None
    form = timepiece_forms.BusinessForm(request.POST or None,
            instance=business)
    if form.is_valid():
        business = form.save()
        url = reverse('view_business', args=(business.pk,))
        return HttpResponseRedirect(url)
    return render(request, 'timepiece/business/create_edit.html', {
        'business': business,
        'business_form': form,
    })


@permission_required('auth.view_user')
def list_users(request):
    form = timepiece_forms.SearchForm(request.GET)
    users = User.objects.all().order_by('last_name')
    if form.is_valid() and 'search' in request.GET:
        search = form.cleaned_data['search']
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
        if users.count() == 1:
            url = request.REQUEST.get('next',
                    reverse('view_user', args=(users[0].id,)))
            return HttpResponseRedirect(url)
    return render(request, 'timepiece/user/list.html', {
        'form': form,
        'users': users.select_related(),
    })


@permission_required('auth.view_user')
@transaction.commit_on_success
def view_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    add_project_form = timepiece_forms.SelectProjectForm()
    return render(request, 'timepiece/user/view.html', {
        'user': user,
        'add_project_form': add_project_form,
    })


@permission_required('auth.add_user')
@permission_required('auth.change_user')
def create_edit_user(request, user_id=None):
    user = get_object_or_404(User, pk=user_id) if user_id else None
    form = timepiece_forms.EditPersonForm(request.POST or None,
            instance=user)
    if form.is_valid():
        user = form.save()
        url = request.REQUEST.get('next',
                reverse('view_user', args=(user.pk,)))
        return HttpResponseRedirect(url)
    return render(request, 'timepiece/user/create_edit.html', {
        'user': user,
        'form': form,
    })


@permission_required('timepiece.view_project')
def list_projects(request):
    form = timepiece_forms.ProjectSearchForm(request.GET or None)
    if form.is_valid() and ('search' in request.GET or 'status' in
            request.GET):
        search, status = form.save()
        query = Q(name__icontains=search) | Q(description__icontains=search)
        projects = timepiece.Project.objects.filter(query)
        projects = projects.filter(status=status) if status else projects
        if projects.count() == 1:
            url = request.REQUEST.get('next',
                    reverse('view_project', args=(projects.get().id,)))
            return HttpResponseRedirect(url)
    else:
        projects = timepiece.Project.objects.all()

    return render(request, 'timepiece/project/list.html', {
        'form': form,
        'projects': projects.select_related('business'),
    })


@permission_required('timepiece.view_project')
@transaction.commit_on_success
def view_project(request, project_id):
    project = get_object_or_404(timepiece.Project, pk=project_id)
    add_user_form = timepiece_forms.SelectUserForm()
    return render(request, 'timepiece/project/view.html', {
        'project': project,
        'add_user_form': add_user_form,
    })


@csrf_exempt
@require_POST
@permission_required('timepiece.add_projectrelationship')
@transaction.commit_on_success
def create_relationship(request):
    user_id = request.REQUEST.get('user_id', None)
    project_id = request.REQUEST.get('project_id', None)
    url = reverse('dashboard')  # Default if nothing else comes up

    project = None
    if project_id:
        project = get_object_or_404(timepiece.Project, pk=project_id)
        url = reverse('view_project', args=(project_id,))
    else:  # Adding a user to a specific project
        project_form = timepiece_forms.SelectProjectForm(request.POST)
        if project_form.is_valid():
            project = project_form.save()

    user = None
    if user_id:
        user = get_object_or_404(User, pk=user_id)
        url = reverse('view_user', args=(user_id,))
    else:  # Adding a project to a specific user
        user_form = timepiece_forms.SelectUserForm(request.POST)
        if user_form.is_valid():
            user = user_form.save()

    if user and project:
        timepiece.ProjectRelationship.objects.get_or_create(
                user=user, project=project)

    url = request.REQUEST.get('next', url)
    return HttpResponseRedirect(url)


@csrf_exempt
@permission_required('timepiece.delete_projectrelationship')
@transaction.commit_on_success
def delete_relationship(request):
    user_id = request.REQUEST.get('user_id', None)
    project_id = request.REQUEST.get('project_id', None)
    rel = get_object_or_404(timepiece.ProjectRelationship,
            user__id=user_id, project__id=project_id)
    if request.method == 'POST':
        rel.delete()
        url = request.REQUEST.get('next',
                reverse('view_project', args=(rel.project.pk,)))
        return HttpResponseRedirect(url)
    return render(request, 'timepiece/relationship/delete.html', {
        'user': rel.user,
        'project': rel.project,
    })


@permission_required('timepiece.change_projectrelationship')
@transaction.commit_on_success
def edit_relationship(request):
    user_id = request.REQUEST.get('user_id', None)
    project_id = request.REQUEST.get('project_id', None)
    rel = get_object_or_404(timepiece.ProjectRelationship,
            user__id=user_id, project__id=project_id)
    data = request.POST if request.method == 'POST' else None
    form = timepiece_forms.ProjectRelationshipForm(data, instance=rel)
    if request.method == 'POST' and form.is_valid():
        rel = form.save()
        url = request.REQUEST.get('next',
                reverse('view_project', args=(project_id,)))
        return HttpResponseRedirect(url)
    return render(request, 'timepiece/relationship/edit.html', {
        'user': rel.user,
        'project': rel.project,
        'relationship_form': form,
    })


@permission_required('timepiece.add_project')
@permission_required('timepiece.change_project')
def create_edit_project(request, project_id=None):
    project = get_object_or_404(timepiece.Project, pk=project_id) if project_id else None
    form = timepiece_forms.ProjectForm(request.POST or None, instance=project)
    if request.POST and form.is_valid():
        project = form.save()
        project.save()
        url = request.REQUEST.get('next',
                reverse('view_project', args=(project.id,)))
        return HttpResponseRedirect(url)
    return render(request, 'timepiece/project/create_edit.html', {
        'project': project,
        'project_form': form,
    })


@permission_required('timepiece.view_payroll_summary')
def report_payroll_summary(request):
    date = timezone.now() - relativedelta(months=1)
    from_date = utils.get_month_start(date).date()
    to_date = from_date + relativedelta(months=1)

    year_month_form = timepiece_forms.YearMonthForm(request.GET or None,
        initial={'month': from_date.month, 'year': from_date.year})

    if year_month_form.is_valid():
        from_date, to_date = year_month_form.save()
    last_billable = utils.get_last_billable_day(from_date)
    projects = utils.get_setting('TIMEPIECE_PAID_LEAVE_PROJECTS')
    weekQ = Q(end_time__gt=utils.get_week_start(from_date),
              end_time__lt=last_billable + datetime.timedelta(days=1))
    monthQ = Q(end_time__gt=from_date, end_time__lt=to_date)
    workQ = ~Q(project__in=projects.values())
    statusQ = Q(status='invoiced') | Q(status='approved')
    # Weekly totals
    week_entries = timepiece.Entry.objects.date_trunc('week').filter(
        weekQ, statusQ, workQ
    )
    date_headers = utils.generate_dates(from_date, last_billable, by='week')
    weekly_totals = list(utils.project_totals(week_entries, date_headers,
                                              'total', overtime=True))
    # Monthly totals
    leave = timepiece.Entry.objects.filter(monthQ, ~workQ
                                  ).values('user', 'hours', 'project__name')
    extra_values = ('project__type__label',)
    month_entries = timepiece.Entry.objects.date_trunc('month', extra_values)
    month_entries_valid = month_entries.filter(monthQ, statusQ, workQ)
    labels, monthly_totals = utils.payroll_totals(month_entries_valid, leave)
    # Unapproved and unverified hours
    entries = timepiece.Entry.objects.filter(monthQ).order_by()  # No ordering
    user_values = ['user__pk', 'user__first_name', 'user__last_name']
    unverified = entries.filter(status='unverified', user__is_active=True) \
                        .values_list(*user_values).distinct()
    unapproved = entries.filter(status='verified') \
                        .values_list(*user_values).distinct()
    return render(request, 'timepiece/reports/payroll_summary.html', {
        'from_date': from_date,
        'year_month_form': year_month_form,
        'date_headers': date_headers,
        'weekly_totals': weekly_totals,
        'monthly_totals': monthly_totals,
        'unverified': unverified,
        'unapproved': unapproved,
        'labels': labels,
    })


@login_required
def edit_settings(request):
    user = request.user
    profile, created = timepiece.UserProfile.objects.get_or_create(user=user)
    if request.method == 'POST':
        user_form = timepiece_forms.UserForm(request.POST, instance=user)
        profile_form = timepiece_forms.UserProfileForm(
                request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.info(request, 'Your settings have been updated.')
            next_url = request.REQUEST.get('next', None)
            if next_url:
                try:
                    resolve(next_url)
                except Http404:
                    next_url = None
            next_url = next_url or reverse('dashboard')
            return HttpResponseRedirect(next_url)
    else:
        profile_form = timepiece_forms.UserProfileForm(instance=profile)
        user_form = timepiece_forms.UserForm(instance=user)
    return render(request, 'timepiece/user/settings.html', {
        'profile_form': profile_form,
        'user_form': user_form,
    })


class ContractDetail(DetailView):
    template_name = 'timepiece/contract/view.html'
    model = timepiece.ProjectContract
    context_object_name = 'contract'
    pk_url_kwarg = 'pk'  # This parameter was introduced in Django 1.4.
                         # When we drop support for Django 1.3, we can
                         # change this to contract_id for consistency of the
                         # URL structure.

    @method_decorator(permission_required('timepiece.add_projectcontract'))
    def dispatch(self, *args, **kwargs):
        return super(ContractDetail, self).dispatch(*args, **kwargs)


class ContractList(ListView):
    template_name = 'timepiece/contract/list.html'
    model = timepiece.ProjectContract
    context_object_name = 'contracts'
    queryset = timepiece.ProjectContract.objects.filter(status='current')\
            .order_by('name')

    @method_decorator(permission_required('timepiece.add_projectcontract'))
    def dispatch(self, *args, **kwargs):
        return super(ContractList, self).dispatch(*args, **kwargs)


class DeleteView(TemplateView):
    model = None
    url_name = None
    permissions = None
    form_class = timepiece_forms.DeleteForm
    template_name = 'timepiece/delete_object.html'
    param = None

    def dispatch(self, request, *args, **kwargs):
        for permission in self.permissions:
            if not request.user.has_perm(permission):
                messages.info(request,
                        'You do not have permission to access that.')
                return HttpResponseRedirect(
                        utils.reverse_lazy('dashboard'))
        return super(DeleteView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        instance = self.get_queryset(**kwargs)
        form = self.form_class(request.POST, instance=instance)
        msg = '{0} could not be successfully deleted.'.format(instance)

        if form.is_valid():
            if form.save():
                msg = '{0} was successfully deleted.'.format(instance)

        messages.info(request, msg)
        return HttpResponseRedirect(utils.reverse_lazy(self.url_name))

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(*args, **kwargs)
        return self.render_to_response(context)

    def get_queryset(self, **kwargs):
        pk = kwargs.get(self.param, None)
        return get_object_or_404(self.model, pk=pk)

    def get_context_data(self, *args, **kwargs):
        context = super(DeleteView, self).get_context_data(*args, **kwargs)
        context['object'] = self.get_queryset(**kwargs)
        return context


class DeleteUserView(DeleteView):
    model = User
    url_name = 'list_users'
    permissions = ('auth.add_user', 'auth.change_user',)
    param = 'user_id'


class DeleteBusinessView(DeleteView):
    model = timepiece.Business
    url_name = 'list_businesses'
    permissions = ('timepiece.add_business',)
    param = 'business_id'


class DeleteProjectView(DeleteView):
    model = timepiece.Project
    url_name = 'list_projects'
    permissions = ('timepiece.add_project', 'timepiece.change_project',)
    param = 'project_id'


class ReportMixin(object):
    """Common data for the Hourly & Billable Hours reports."""

    @method_decorator(permission_required('timepiece.view_entry_summary'))
    def dispatch(self, request, *args, **kwargs):
        return super(ReportMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Processes form data to get relevant entries & date_headers."""
        context = super(ReportMixin, self).get_context_data(**kwargs)

        form = self.get_form()
        if form.is_valid():
            data = form.cleaned_data
            start, end = form.save()
            entryQ = self.get_entry_query(start, end, data)
            trunc = data['trunc']
            if entryQ:
                vals = ('pk', 'activity', 'project', 'project__name',
                        'project__status')
                entries = timepiece.Entry.objects.date_trunc(trunc,
                        extra_values=vals).filter(entryQ)
            else:
                entries = timepiece.Entry.objects.none()

            end = end - relativedelta(days=1)
            date_headers = utils.generate_dates(start, end, by=trunc)
            context.update({
                'from_date': start,
                'to_date': end,
                'date_headers': date_headers,
                'entries': entries,
                'filter_form': form,
                'trunc': trunc,
            })
        else:
            context.update({
                'from_date': None,
                'to_date': None,
                'date_headers': [],
                'entries': timepiece.Entry.objects.none(),
                'filter_form': form,
                'trunc': '',
            })

        return context

    def get_entry_query(self, start, end, data):
        """Builds timepiece.Entry query from form data."""
        # Entry types.
        incl_billable = data.get('billable', True)
        incl_nonbillable = data.get('non_billable', True)
        incl_leave = data.get('paid_leave', True)

        # If no types are selected, shortcut & return nothing.
        if not any((incl_billable, incl_nonbillable, incl_leave)):
            return None

        # All entries must meet time period requirements.
        basicQ = Q(end_time__gte=start, end_time__lt=end)

        # Filter by project for HourlyReport.
        projects = data.get('projects', None)
        basicQ &= Q(project__in=projects) if projects else Q()

        # Filter by user, activity, and project type for BillableReport.
        if 'people' in data:
            basicQ &= Q(user__in=data.get('people'))
        if 'activities' in data:
            basicQ &= Q(activity__in=data.get('activities'))
        if 'project_types' in data:
            basicQ &= Q(project__type__in=data.get('project_types'))

        # If all types are selected, no further filtering is required.
        if all((incl_billable, incl_nonbillable, incl_leave)):
            return basicQ

        # Filter by whether a project is billable or non-billable.
        billableQ = None
        if incl_billable and not incl_nonbillable:
            billableQ = Q(activity__billable=True,
                    project__type__billable=True)
        if incl_nonbillable and not incl_billable:
            billableQ = Q(activity__billable=False) |\
                    Q(project__type__billable=False)

        # Filter by whether the entry is paid leave.
        leave_ids = utils.get_setting('TIMEPIECE_PAID_LEAVE_PROJECTS').values()
        leaveQ = Q(project__in=leave_ids)
        if incl_leave:
            extraQ = (leaveQ | billableQ) if billableQ else leaveQ
        else:
            extraQ = (~leaveQ & billableQ) if billableQ else ~leaveQ

        return basicQ & extraQ

    def get_headers(self, date_headers, from_date, to_date, trunc):
        """Adjust date headers & get range headers."""
        date_headers = list(date_headers)

        # Earliest date should be no earlier than from_date.
        if date_headers and date_headers[0] < from_date:
            date_headers[0] = from_date

        # When organizing by week or month, create a list of the range for
        # each date header.
        if date_headers and trunc != 'day':
            count = len(date_headers)
            range_headers = [0] * count
            for i in range(count - 1):
                range_headers[i] = (date_headers[i], date_headers[i + 1] -
                        relativedelta(days=1))
            range_headers[count - 1] = (date_headers[count - 1], to_date)
        else:
            range_headers = date_headers
        return date_headers, range_headers

    def get_previous_month(self):
        """Returns date range for the previous full month."""
        end = utils.get_month_start() - relativedelta(days=1)
        end = utils.to_datetime(end)
        start = utils.get_month_start(end)
        return start, end


class HourlyReport(ReportMixin, CSVMixin, TemplateView):
    template_name = 'timepiece/reports/hourly.html'

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file."""
        content = []
        date_headers = context['date_headers']

        headers = ['Name']
        headers.extend([date.strftime('%m/%d/%Y') for date in date_headers])
        headers.append('Total')
        content.append(headers)

        if self.export_projects:
            key = 'By Project'
        else:
            key = 'By User'

        summaries = context['summaries']
        summary = summaries[key] if key in summaries else []
        for rows, totals in summary:
            for name, user_id, hours in rows:
                data = [name]
                data.extend(hours)
                content.append(data)
            total = ['Totals']
            total.extend(totals)
            content.append(total)
        return content

    @property
    def defaults(self):
        """Default filter form data when no GET data is provided."""
        # Set default date span to previous week.
        (start, end) = utils.get_week_window(
            timezone.now() - relativedelta(days=7)
        )
        return {
            'from_date': start,
            'to_date': end,
            'billable': True,
            'non_billable': True,
            'paid_leave': True,
            'trunc': 'day',
            'projects': [],
        }

    def get(self, request, *args, **kwargs):
        self.export_users = request.GET.get('export_users', False)
        self.export_projects = request.GET.get('export_projects', False)
        context = self.get_context_data()
        if self.export_users or self.export_projects:
            kls = CSVMixin
        else:
            kls = TemplateView
        return kls.render_to_response(self, context)

    def get_context_data(self, **kwargs):
        context = super(HourlyReport, self).get_context_data(**kwargs)

        # Sum the hours totals for each person & interval.
        entries = context['entries']
        date_headers = context['date_headers']

        summaries = {}
        if context['entries']:
            summaries['By User'] = utils.project_totals(
                    entries.order_by('user__last_name', 'user__id', 'date'),
                    date_headers, 'total', total_column=True, by='user')
            summaries['By Project'] = utils.project_totals(
                    entries.order_by('project__name', 'project__id', 'date'),
                    date_headers, 'total', total_column=True, by='project')

        # Adjust date headers & create range headers.
        from_date = context['from_date']
        from_date = utils.add_timezone(from_date) if from_date else None
        to_date = context['to_date']
        to_date = utils.add_timezone(to_date) if to_date else None
        trunc = context['trunc']
        date_headers, range_headers = self.get_headers(date_headers,
                from_date, to_date, trunc)

        context.update({
            'date_headers': date_headers,
            'summaries': summaries,
            'range_headers': range_headers,
        })
        return context

    def get_filename(self, context):
        request = self.request.GET.copy()
        from_date = request.get('from_date')
        to_date = request.get('to_date')
        return 'hours_{0}_to_{1}_by_{2}.csv'.format(from_date, to_date,
            context.get('trunc', ''))

    def get_form(self):
        data = self.request.GET or self.defaults
        return timepiece_forms.ProjectFiltersForm(data)


class BillableHours(ReportMixin, TemplateView):
    template_name = 'timepiece/reports/billable_hours.html'

    @property
    def defaults(self):
        """Default filter form data when no GET data is provided."""
        start, end = self.get_previous_month()
        return {
            'from_date': start,
            'to_date': end,
            'trunc': 'week',
        }

    def get_context_data(self, **kwargs):
        context = super(BillableHours, self).get_context_data(**kwargs)

        entries = context['entries']
        date_headers = context['date_headers']
        data_map = self.get_hours_data(entries, date_headers)

        from_date = context['from_date']
        to_date = context['to_date']
        trunc = context['trunc']
        kwargs = {trunc + 's': 1}  # For relativedelta

        keys = sorted(data_map.keys())
        data_list = [['Date', 'Billable', 'Non-billable']]
        for i in range(len(keys)):
            start = keys[i]
            start = start if start >= from_date else from_date
            end = start + relativedelta(**kwargs) - relativedelta(days=1)
            end = end if end <= to_date else to_date

            if start != end:
                label = ' - '.join([d.strftime('%b %d') for d in (start, end)])
            else:
                label = start.strftime('%b %d')
            billable = data_map[keys[i]]['billable']
            nonbillable = data_map[keys[i]]['nonbillable']
            data_list.append([label, billable, nonbillable])

        context.update({
            'data': json.dumps(data_list, cls=DecimalEncoder),
        })
        return context

    def get_form(self):
        if self.request.GET:
            return timepiece_forms.BillableHoursForm(self.request.GET)
        else:
            # Select all available users, activities, and project types.
            return timepiece_forms.BillableHoursForm(self.defaults,
                    select_all=True)

    def get_hours_data(self, entries, date_headers):
        """Sum billable and non-billable hours across all users."""
        project_totals = utils.project_totals(entries, date_headers,
                total_column=False) if entries else []

        data_map = {}
        for rows, totals in project_totals:
            for user, user_id, periods in rows:
                for period in periods:
                    day = period['day']
                    if day not in data_map:
                        data_map[day] = {'billable': 0, 'nonbillable': 0}
                    data_map[day]['billable'] += period['billable']
                    data_map[day]['nonbillable'] += period['nonbillable']

        return data_map


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

        return super(ScheduleMixin, self).dispatch(request, *args,
                **kwargs)

    def get_hours_for_week(self, start=None):
        week_start = start if start else self.week_start
        week_end = week_start + relativedelta(days=7)

        return timepiece.ProjectHours.objects.filter(
            week_start__gte=week_start, week_start__lt=week_end)


class ScheduleView(ScheduleMixin, TemplateView):
    template_name = 'timepiece/schedule/view.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('timepiece.can_clock_in'):
            return HttpResponseRedirect(reverse('auth_login'))

        return super(ScheduleView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ScheduleView, self).get_context_data(**kwargs)

        initial = {'week_start': self.week_start}
        form = timepiece_forms.ProjectHoursSearchForm(initial=initial)

        project_hours = utils.get_project_hours_for_week(self.week_start) \
            .filter(published=True)
        people = utils.get_people_from_project_hours(project_hours)
        id_list = [person[0] for person in people]
        projects = []

        func = lambda o: o['project__id']
        for project, entries in groupby(project_hours, func):
            entries = list(entries)
            proj_id = entries[0]['project__id']
            name = entries[0]['project__name']
            row = [None for i in range(len(id_list))]
            for entry in entries:
                index = id_list.index(entry['user__id'])
                hours = entry['hours']
                row[index] = row[index] + hours if row[index] else hours
            projects.append((proj_id, name, row))

        context.update({
            'form': form,
            'week': self.week_start,
            'prev_week': self.week_start - relativedelta(days=7),
            'next_week': self.week_start + relativedelta(days=7),
            'people': people,
            'project_hours': project_hours,
            'projects': projects
        })
        return context


class EditScheduleView(ScheduleMixin, TemplateView):
    template_name = 'timepiece/schedule/edit.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('timepiece.add_projecthours'):
            return HttpResponseRedirect(reverse('view_schedule'))

        return super(EditScheduleView, self).dispatch(request, *args,
                **kwargs)

    def get_context_data(self, **kwargs):
        context = super(EditScheduleView, self).get_context_data(**kwargs)

        form = timepiece_forms.ProjectHoursSearchForm(initial={
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
            'week_start': self.week_start.strftime('%Y-%m-%d')
        }
        url = '?'.join((reverse('edit_schedule'),
            urllib.urlencode(param),))

        return HttpResponseRedirect(url)


class ScheduleAjaxView(ScheduleMixin, View):
    permissions = ('timepiece.add_projecthours',)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_perm('timepiece.add_projecthours'):
            return HttpResponseRedirect(reverse('auth_login'))

        return super(ScheduleAjaxView, self).dispatch(request, *args,
                **kwargs)

    def get_instance(self, data, week_start):
        try:
            user = User.objects.get(pk=data.get('user', None))
            project = timepiece.Project.objects.get(
                pk=data.get('project', None))
            hours = data.get('hours', None)
            week = datetime.datetime.strptime(week_start, '%Y-%m-%d').date()

            ph = timepiece.ProjectHours.objects.get(user=user, project=project,
                week_start=week)
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
            content_type=ContentType.objects.get_for_model(timepiece.Entry),
            codename='can_clock_in'
        )
        project_hours = self.get_hours_for_week().values(
            'id', 'user', 'user__first_name', 'user__last_name',
            'project', 'hours', 'published'
        ).order_by('-project__type__billable', 'project__name',
            'user__first_name', 'user__last_name')
        inner_qs = project_hours.values_list('project', flat=True)
        projects = timepiece.Project.objects.filter(pk__in=inner_qs).values() \
            .order_by('name')
        all_projects = timepiece.Project.objects.values('id', 'name')
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
            mimetype='application/json')

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
                timepiece.ProjectHours.objects.bulk_create(
                    duplicate_builder(queryset, new_date)
                )
            except AttributeError:
                for entry in duplicate_builder(queryset, new_date):
                    entry.save()
            msg = 'Project hours were copied'
            messages.info(self.request, msg)

        this_week = datetime.datetime.strptime(week_update, '%Y-%m-%d').date()
        prev_week = this_week - relativedelta(days=7)
        prev_week_qs = self.get_hours_for_week(prev_week)
        this_week_qs = self.get_hours_for_week(this_week)

        param = {
            'week_start': week_update
        }
        url = '?'.join((reverse('edit_schedule'),
            urllib.urlencode(param),))

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

        form = timepiece_forms.ProjectHoursForm(self.request.POST,
            instance=instance)

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


class ScheduleDetailView(ScheduleMixin, View):
    permissions = ('timepiece.add_projecthours',)

    def delete(self, request, *args, **kwargs):
        """Remove a project from the database."""
        assignment_id = kwargs.get('assignment_id', None)

        if assignment_id:
            timepiece.ProjectHours.objects.filter(pk=assignment_id).delete()
            return HttpResponse('ok', mimetype='text/plain')

        return HttpResponse('', status=500)


@login_required
@permission_required('timepiece.view_entry_summary')
def report_productivity(request):
    report = []
    organize_by = None

    form = timepiece_forms.ProductivityReportForm(request.GET or None)
    if form.is_valid():
        project = form.cleaned_data['project']
        organize_by = form.cleaned_data['organize_by']
        export = request.GET.get('export', False)

        actualsQ = Q(project=project, end_time__isnull=False)
        actuals = timepiece.Entry.objects.filter(actualsQ)
        projections = timepiece.ProjectHours.objects.filter(project=project)
        entry_count = actuals.count() + projections.count()

        if organize_by == 'week' and entry_count > 0:
            # Determine the project's time range.
            amin, amax, pmin, pmax = (None, None, None, None)
            if actuals.count() > 0:
                amin = actuals.aggregate(Min('start_time')).values()[0]
                amin = utils.get_week_start(amin).date()
                amax = actuals.aggregate(Max('start_time')).values()[0]
                amax = utils.get_week_start(amax).date()
            if projections.count() > 0:
                pmin = projections.aggregate(Min('week_start')).values()[0]
                pmax = projections.aggregate(Max('week_start')).values()[0]
            current = min(amin, pmin) if (amin and pmin) else (amin or pmin)
            latest = max(amax, pmax) if (amax and pmax) else (amax or pmax)

            # Report for each week during the project's time range.
            while current <= latest:
                next_week = current + relativedelta(days=7)
                actual_hours = actuals.filter(start_time__gte=current,
                        start_time__lt=next_week).aggregate(
                        Sum('hours')).values()[0]
                projected_hours = projections.filter(week_start__gte=current,
                        week_start__lt=next_week).aggregate(
                        Sum('hours')).values()[0]
                report.append([current.strftime('%Y-%m-%d'),
                        actual_hours or 0, projected_hours or 0])
                current = next_week

        elif organize_by == 'person' and entry_count > 0:
            # Determine all people who worked on or were assigned to the
            # project.
            vals = ('user', 'user__first_name', 'user__last_name')
            apeople = list(actuals.values_list(*vals).distinct())
            ppeople = list(projections.values_list(*vals).distinct())
            key = lambda x: (x[1] + x[2]).lower()  # Sort by name
            people = sorted(list(set(apeople + ppeople)), key=key)

            # Report for each person.
            for person in people:
                name = '{0} {1}'.format(person[1], person[2])
                actual_hours = actuals.filter(user=person[0]) \
                        .aggregate(Sum('hours')).values()[0]
                projected_hours = projections.filter(user=person[0]) \
                        .aggregate(Sum('hours')).values()[0]
                report.append([name, actual_hours or 0, projected_hours or 0])

        col_headers = [organize_by.title(), 'Worked Hours', 'Assigned Hours']
        report.insert(0, col_headers)

        if export:
            response = HttpResponse(content_type='text/csv')
            filename = '{0}_productivity'.format(project.name)
            content_disp = 'attachment; filename={0}.csv'.format(filename)
            response['Content-Disposition'] = content_disp
            writer = csv.writer(response)
            for row in report:
                writer.writerow(row)
            return response

    return render(request, 'timepiece/reports/productivity.html', {
        'form': form,
        'report': json.dumps(report, cls=DecimalEncoder),
        'type': organize_by or '',
        'total_worked': sum([r[1] for r in report[1:]]),
        'total_assigned': sum([r[2] for r in report[1:]]),
    })
