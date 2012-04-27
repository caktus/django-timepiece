import urllib
import csv
import datetime
import calendar
import math
import urllib

from decimal import Decimal
from dateutil.relativedelta import relativedelta
from dateutil import rrule

from django.contrib import messages
from django.template import RequestContext
from django.shortcuts import (render_to_response, get_object_or_404, redirect,
                              render)
from django.core.urlresolvers import reverse, resolve
from django.http import HttpResponse, HttpResponseRedirect
from django.http import  Http404, HttpResponseForbidden
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.contrib.auth import models as auth_models
from django.db.models import Sum, Count, Q, F
from django.db import transaction
from django.conf import settings
from django.utils.datastructures import SortedDict
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView
from django.views.generic import UpdateView, ListView, DetailView
from django.utils.decorators import method_decorator

from timepiece.utils import render_with

from timepiece import models as timepiece
from timepiece import utils
from timepiece import forms as timepiece_forms
from timepiece.templatetags.timepiece_tags import seconds_to_hours


@login_required
def quick_search(request):
    if request.GET:
        form = timepiece_forms.QuickSearchForm(request.GET)
        if form.is_valid():
            return HttpResponseRedirect(form.save())
    raise Http404


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
        raise NotImplemented("You must implement this in the subclass")

    def convert_context_to_csv(self, context):
        "Convert the context dictionary into a CSV file"
        raise NotImplemented("You must implement this in the subclass")


@login_required
@render_with('timepiece/time-sheet/dashboard.html')
def view_entries(request):
    week_start = utils.get_week_start()
    entries = timepiece.Entry.objects.select_related(
        'project__business',
    ).filter(
        user=request.user,
        end_time__gte=week_start,
    ).select_related('project', 'activity', 'location')
    today = datetime.date.today()
    assignments = timepiece.ContractAssignment.objects.filter(
        user=request.user,
        user__project_relationships__project=F('contract__project'),
        end_date__gte=today,
        contract__status='current',
    ).order_by('contract__project__type', 'end_date')
    assignments = assignments.select_related('user', 'contract__project__type')
    activity_entries = entries.values(
        'billable',
    ).annotate(sum=Sum('hours')).order_by('-sum')
    others_active_entries = timepiece.Entry.objects.filter(
        end_time__isnull=True,
    ).exclude(
        user=request.user,
    ).select_related('user', 'project', 'activity')
    my_active_entries = timepiece.Entry.objects.select_related(
        'project__business',
    ).only(
        'user', 'project', 'activity', 'start_time'
    ).filter(
        user=request.user,
        end_time__isnull=True,
    )
#     temporarily disabled until the allocations represent accurate goals
#     -TM 6/27
    allocations = []
    allocated_projects = timepiece.Project.objects.none()
#    allocations = timepiece.AssignmentAllocation.objects.during_this_week(
#        request.user
#        ).order_by('assignment__contract__project__name')
#    allocated_projects = allocations.values_list(
#    'assignment__contract__project',)

    project_entries = entries.exclude(
        project__in=allocated_projects,
    ).values(
        'project__name', 'project__pk'
    ).annotate(sum=Sum('hours')).order_by('project__name')
    schedule = timepiece.PersonSchedule.objects.filter(
                                    user=request.user)
    context = {
        'this_weeks_entries': entries.order_by('-start_time'),
        'assignments': assignments,
        'allocations': allocations,
        'schedule': schedule,
        'project_entries': project_entries,
        'activity_entries': activity_entries,
        'others_active_entries': others_active_entries,
        'my_active_entries': my_active_entries,
    }
    return context


@permission_required('timepiece.can_clock_in')
@transaction.commit_on_success
def clock_in(request):
    """For clocking the user into a project"""
    if request.POST:
        form = timepiece_forms.ClockInForm(request.POST, user=request.user)
        if form.is_valid():
            entry = form.save()
            #check that the user is not currently logged into another project.
            #if so, clock them out of all others.
            my_active_entries = timepiece.Entry.no_join.select_related(
                'project__business',
            ).filter(
                user=request.user,
                end_time__isnull=True,
            ).exclude(
                id=entry.id
            )
            #clock_out all open entries one second before the last
            for sec_bump, active_entry in enumerate(my_active_entries):
                active_entry.unpause()
                active_entry.end_time = entry.start_time - \
                    datetime.timedelta(seconds=sec_bump + 1)
                active_entry.save()

            request.user.message_set.create(
                message='You have clocked into %s' % entry.project)
            return HttpResponseRedirect(reverse('timepiece-entries'))
        else:
            request.user.message_set.create(
                message='Please correct the errors below.')
    else:
        initial = dict([(k, request.GET[k]) for k in request.GET.keys()])
        form = timepiece_forms.ClockInForm(user=request.user, initial=initial)
    return render_to_response(
        'timepiece/time-sheet/entry/clock_in.html',
        {'form': form},
        context_instance=RequestContext(request),
    )


@permission_required('timepiece.can_clock_out')
def clock_out(request, entry_id):
    entry = get_object_or_404(
        timepiece.Entry,
        pk=entry_id,
        user=request.user,
        end_time__isnull=True,
    )
    if request.POST:
        form = timepiece_forms.ClockOutForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save()
            request.user.message_set.create(message="You've been clocked out.")
            return HttpResponseRedirect(reverse('timepiece-entries'))
        else:
            request.user.message_set.create(
                message='Please correct the errors below.')
    else:
        form = timepiece_forms.ClockOutForm(instance=entry)
    context = {
        'form': form,
        'entry': entry,
    }
    return render_to_response(
        'timepiece/time-sheet/entry/clock_out.html',
        context,
        context_instance=RequestContext(request),
    )


@permission_required('timepiece.can_pause')
def toggle_paused(request, entry_id):
    """
    Allow the user to pause and unpause their open entries.  If this method is
    invoked on an entry that is not paused, it will become paused.  If this
    method is invoked on an entry that is already paused, it will unpause it.
    Then the user will be redirected to their log entry list.
    """

    try:
        # retrieve the log entry
        entry = timepiece.Entry.no_join.get(pk=entry_id,
                                  user=request.user,
                                  end_time__isnull=True)
    except:
        # create an error message for the user
        request.user.message_set.create(
            message='The entry could not be paused.  Please try again.')
    else:
        # toggle the paused state
        entry.toggle_paused()

        # save it
        entry.save()

        if entry.is_paused:
            action = 'paused'
        else:
            action = 'resumed'

        delta = datetime.datetime.now() - entry.start_time
        seconds = delta.seconds - entry.seconds_paused
        seconds += delta.days * 86400

        if seconds < 3600:
            seconds /= 60.0
            duration = "You've clocked %d minutes." % seconds
        else:
            seconds /= 3600.0
            duration = "You've clocked %.2f hours." % seconds

        message = 'The log entry has been %s. %s' % (action, duration)

        # create a message that can be displayed to the user
        request.user.message_set.create(message=message)

    # redirect to the log entry list
    return HttpResponseRedirect(reverse('timepiece-entries'))


@permission_required('timepiece.change_entry')
@render_with('timepiece/time-sheet/entry/add_update_entry.html')
def create_edit_entry(request, entry_id=None):
    if entry_id:
        try:
            entry = timepiece.Entry.no_join.get(
                pk=entry_id,
                user=request.user,
            )
            if not entry.is_editable:
                raise Http404

        except timepiece.Entry.DoesNotExist:
            raise Http404

    else:
        entry = None

    if request.POST:
        form = timepiece_forms.AddUpdateEntryForm(
            request.POST,
            instance=entry,
            user=request.user,
        )
        if form.is_valid():
            entry = form.save()
            if entry_id:
                message = 'The entry has been updated successfully.'
            else:
                message = 'The entry has been created successfully.'
            request.user.message_set.create(message=message)
            return HttpResponseRedirect(reverse('timepiece-entries'))
        else:
            request.user.message_set.create(
                message='Please fix the errors below.',
            )
    else:
        initial = dict([(k, request.GET[k]) for k in request.GET.keys()])
        form = timepiece_forms.AddUpdateEntryForm(
            instance=entry,
            user=request.user,
            initial=initial,
        )

    return {
        'form': form,
        'entry': entry,
    }


@permission_required('timepiece.delete_entry')
def delete_entry(request, entry_id):
    """
    Give the user the ability to delete a log entry, with a confirmation
    beforehand.  If this method is invoked via a GET request, a form asking
    for a confirmation of intent will be presented to the user.  If this method
    is invoked via a POST request, the entry will be deleted.
    """

    try:
        # retrieve the log entry
        entry = timepiece.Entry.no_join.get(pk=entry_id,
                                  user=request.user)
    except:
        # entry does not exist
        request.user.message_set.create(message='No such log entry.')
        return HttpResponseRedirect(reverse('timepiece-entries'))

    if request.method == 'POST':
        key = request.POST.get('key', None)
        if key and key == entry.delete_key:
            entry.delete()
            request.user.message_set.create(message='Entry deleted.')
            return HttpResponseRedirect(reverse('timepiece-entries'))
        else:
            request.user.message_set.create(
                message='You are not authorized to delete this entry!')

    return render_to_response('timepiece/time-sheet/entry/delete_entry.html',
                              {'entry': entry},
                              context_instance=RequestContext(request))


@permission_required('timepiece.view_entry_summary')
@render_with('timepiece/time-sheet/reports/general_ledger.html')
def summary(request, username=None):
    if request.GET:
        form = timepiece_forms.DateForm(request.GET)
        if form.is_valid():
            from_date, to_date = form.save()
    else:
        form = timepiece_forms.DateForm()
        from_date, to_date = None, None
    entries = timepiece.Entry.no_join.values(
        'project__id',
        'project__business__id',
        'project__name',
    ).order_by(
        'project__id',
        'project__business__id',
        'project__name',
    )
    dates = Q()
    if from_date:
        dates &= Q(start_time__gte=from_date)
    if to_date:
        dates &= Q(end_time__lte=to_date)
    project_totals = entries.filter(dates).annotate(total_hours=Sum('hours'))
    project_totals = project_totals.order_by('project__name')
    total_hours = timepiece.Entry.objects.filter(dates).aggregate(
        hours=Sum('hours')
    )['hours']
    people_totals = timepiece.Entry.no_join.values('user', 'user__first_name',
                                                   'user__last_name')
    people_totals = people_totals.order_by('user__last_name').filter(dates)
    people_totals = people_totals.annotate(total_hours=Sum('hours'))
    context = {
        'form': form,
        'project_totals': project_totals,
        'total_hours': total_hours,
        'people_totals': people_totals,
    }
    return context


class ProjectTimesheet(DetailView):
    template_name = 'timepiece/time-sheet/projects/view.html'
    model = timepiece.Project
    context_object_name = 'project'

    @method_decorator(permission_required('timepiece.view_project_time_sheet'))
    def dispatch(self, *args, **kwargs):
        return super(ProjectTimesheet, self).dispatch(*args, **kwargs)

    def get(self, *args, **kwargs):
        if 'csv' in self.request.GET:
            request_get = self.request.GET.copy()
            request_get.pop('csv')
            return_url = reverse('export_project_time_sheet',
                                 kwargs={'pk': self.get_object().pk})
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
            from_date = utils.get_month_start(datetime.datetime.today()).date()
            to_date = from_date + relativedelta(months=1)
        entries_qs = timepiece.Entry.objects
        entries_qs = entries_qs.timespan(from_date, span='month').filter(
            project=project
        )
        month_entries = entries_qs.date_trunc('month', True).order_by(
            'start_time'
        )
        total = entries_qs.aggregate(hours=Sum('hours'))['hours']
        user_entries = entries_qs.order_by().values(
            'user__first_name', 'user__last_name').annotate(
            sum=Sum('hours')).order_by('-sum'
        )
        activity_entries = entries_qs.order_by().values(
            'activity__name').annotate(
            sum=Sum('hours')).order_by('-sum'
        )
        return {
            'project': project,
            'year_month_form': year_month_form,
            'from_date': from_date,
            'to_date': to_date - datetime.timedelta(days=1),
            'entries': month_entries,
            'total': total,
            'user_entries': user_entries,
            'activity_entries': activity_entries,
        }


class ProjectTimesheetCSV(CSVMixin, ProjectTimesheet):

    def get_filename(self, context):
        project = self.object.name
        to_date_str = context['to_date'].strftime("%m-%d-%Y")
        return "Project_timesheet {0} {1}".format(project, to_date_str)

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
                ' '.join((entry['user__first_name'],
                          entry['user__last_name'])),
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
def view_person_time_sheet(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if not (request.user.has_perm('timepiece.view_entry_summary') or \
        user.pk == request.user.pk):
        return HttpResponseForbidden('Forbidden')
    year_month_form = timepiece_forms.YearMonthForm(request.GET or None)
    if request.GET and year_month_form.is_valid():
        from_date, to_date = year_month_form.save()
    else:
        from_date = utils.get_month_start(datetime.datetime.today()).date()
        to_date = from_date + relativedelta(months=1)
    entries_qs = timepiece.Entry.objects
    entries_qs = entries_qs.timespan(from_date, span='month').filter(user=user)
    show_approve = show_verify = False
    if request.user.has_perm('timepiece.change_entry') or \
        user == request.user:
        statuses = list(entries_qs.values_list('status', flat=True))
        total_statuses = len(statuses)
        unverified_count = statuses.count('unverified')
        verified_count = statuses.count('verified')
        approved_count = statuses.count('approved')
        show_verify = unverified_count != 0
    if request.user.has_perm('timepiece.change_entry'):
        show_approve = verified_count + approved_count == total_statuses \
        and verified_count > 0 and total_statuses != 0
    month_entries = entries_qs.date_trunc('month', True)
    grouped_totals = utils.grouped_totals(entries_qs) if month_entries else ''
    project_entries = entries_qs.order_by().values(
        'project__name').annotate(sum=Sum('hours')).order_by('-sum')
    summary = timepiece.Entry.summary(user, from_date, to_date)
    context = {
        'year_month_form': year_month_form,
        'from_date': from_date,
        'to_date': to_date - datetime.timedelta(days=1),
        'show_verify': show_verify,
        'show_approve': show_approve,
        'user': user,
        'entries': month_entries,
        'grouped_totals': grouped_totals,
        'project_entries': project_entries,
        'summary': summary,
    }
    return render_to_response('timepiece/time-sheet/people/view.html',
        context, context_instance=RequestContext(request))


@login_required
def change_person_time_sheet(request, action, user_id, from_date):
    user = get_object_or_404(User, pk=user_id)
    admin_verify = request.user.has_perm('timepiece.change_entry')
    if not admin_verify and user != request.user:
        return HttpResponseForbidden('Forbidden')
    try:
        from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d')
    except (ValueError, OverflowError):
        raise Http404
    to_date = from_date + relativedelta(months=1)
    entries = timepiece.Entry.no_join.filter(user=user_id,
                                             end_time__gte=from_date,
                                             end_time__lt=to_date)
    filter_status = {
        'verify': 'unverified',
        'approve': 'verified',
    }
    entries = entries.filter(status=filter_status[action])
    return_url = reverse('view_person_time_sheet', kwargs={'user_id': user_id})
    return_url += '?%s' % urllib.urlencode({
        'year': from_date.year,
        'month': from_date.month,
    })
    if request.POST and request.POST.get('do_action', 'No') == 'Yes':
        update_status = {
            'verify': 'verified',
            'approve': 'approved',
        }
        entries.update(status=update_status[action])
        messages.info(request,
            'Your entries have been %s' % update_status[action])
        return redirect(return_url)
    context = {
        'action': action,
        'user': user,
        'from_date': from_date,
        'to_date': to_date - datetime.timedelta(days=1),
        'return_url': return_url,
        'hours': entries.all().aggregate(s=Sum('hours'))['s'],
    }
    return render_to_response('timepiece/time-sheet/people/change_status.html',
        context, context_instance=RequestContext(request))


@login_required
@transaction.commit_on_success
def confirm_invoice_project(request, project_id, to_date, from_date=None):
    if not request.user.has_perm('timepiece.change_entry'):
        return HttpResponseForbidden('Forbidden')
    try:
        to_date = datetime.datetime.strptime(to_date, '%Y-%m-%d')
        if from_date:
            from_date = datetime.datetime.strptime(from_date, '%Y-%m-%d')
        else:
            from_date = None
    except (ValueError, OverflowError):
        raise Http404
    project = get_object_or_404(timepiece.Project, pk=project_id)
    initial = {
        'project': project,
        'user': request.user,
        'from_date': from_date,
        'to_date': to_date,
    }
    entries_query = {
        'status': "approved",
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

    totals = timepiece.HourGroup.objects.summaries(entries)
    template = 'timepiece/time-sheet/invoice/confirm.html'
    return render_to_response(template, {
        'invoice_form': invoice_form,
        'entries': entries.select_related(),
        'project': project,
        'totals': totals,
        'from_date': from_date,
        'to_date': to_date,
    }, context_instance=RequestContext(request))


@permission_required('timepiece.change_entrygroup')
def invoice_projects(request):
    to_date = utils.get_month_start(datetime.datetime.today()).date()
    from_date = None
    defaults = {
        'to_date': (to_date - relativedelta(days=1)).strftime('%m/%d/%Y'),
    }
    date_form = timepiece_forms.DateForm(request.GET or defaults)
    if request.GET and date_form.is_valid():
        from_date, to_date = date_form.save()
    datesQ = Q()
    datesQ &= Q(end_time__gte=from_date)  if from_date else Q()
    datesQ &= Q(end_time__lt=to_date)  if to_date else Q()
    entries = timepiece.Entry.objects.filter(datesQ)
    project_totals = entries.filter(status='approved',
        project__type__billable=True, project__status__billable=True).values(
        'project__type__pk', 'project__type__label', 'project__name', 'hours',
        'project__pk', 'status', 'project__status__label'
    ).annotate(s=Sum('hours')).order_by('project__type__label',
                                        'project__name', 'status')
    return render_to_response(
        'timepiece/time-sheet/invoice/make_invoice.html', {
        'date_form': date_form,
        'project_totals': project_totals if to_date else [],
        'to_date': to_date - relativedelta(days=1) if to_date else '',
        'from_date': from_date,
    }, context_instance=RequestContext(request))


class InvoiceList(ListView):
    template_name = 'timepiece/time-sheet/invoice/list.html'
    context_object_name = 'invoices'
    queryset = timepiece.EntryGroup.objects.all().order_by('-created')

    @method_decorator(permission_required('timepiece.change_entrygroup'))
    def dispatch(self, *args, **kwargs):
        return super(InvoiceList, self).dispatch(*args, **kwargs)


class InvoiceDetail(DetailView):
    template_name = 'timepiece/time-sheet/invoice/view.html'
    model = timepiece.EntryGroup
    context_object_name = 'invoice'

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


class InvoiceEntryDetail(InvoiceDetail):
    template_name = 'timepiece/time-sheet/invoice/view_entries.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceEntryDetail, self).get_context_data(**kwargs)
        entries = context['entries']
        context.update({
            'total': entries.aggregate(hours=Sum('hours'))['hours'],
        })
        return context


class InvoiceCSV(CSVMixin, InvoiceDetail):

    def get_filename(self, context):
        invoice = context['invoice']
        project = str(invoice.project).replace(' ', '_')
        end_day = invoice.end.strftime("%m-%d-%Y")
        return "Invoice-{0}-{1}".format(project, end_day)

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
    template_name = 'timepiece/time-sheet/invoice/edit.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceEdit, self).get_context_data(**kwargs)
        invoice_form = timepiece_forms.InvoiceForm(instance=self.object)
        context.update({
            'invoice_form': invoice_form,
        })
        return context

    def post(self, request, **kwargs):
        invoice = get_object_or_404(timepiece.EntryGroup, pk=kwargs.get('pk'))
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
    template_name = 'timepiece/time-sheet/invoice/delete.html'

    def post(self, request, **kwargs):
        invoice = get_object_or_404(timepiece.EntryGroup, pk=kwargs.get('pk'))
        if 'delete' in request.POST:
            invoice.delete()
            return HttpResponseRedirect(reverse('list_invoices'))
        else:
            return redirect(reverse('edit_invoice', kwargs=kwargs))


@permission_required('timepiece.change_entrygroup')
def remove_invoice_entry(request, invoice_id, entry_id):
    invoice = get_object_or_404(timepiece.EntryGroup, pk=invoice_id)
    entry = get_object_or_404(timepiece.Entry, pk=entry_id)
    if request.POST:
        entry.status = 'approved'
        entry.entry_group = None
        entry.save()
        kwargs = {'pk': invoice_id}
        return HttpResponseRedirect(reverse('edit_invoice', kwargs=kwargs))
    else:
        context = {
            'invoice': invoice,
            'entry': entry,
        }
        return render_to_response(
            'timepiece/time-sheet/invoice/remove_invoice_entry.html',
            context,
            context_instance=RequestContext(request)
        )


@permission_required('timepiece.view_business')
@render_with('timepiece/business/list.html')
def list_businesses(request):
    form = timepiece_forms.SearchForm(request.GET)
    if form.is_valid() and 'search' in request.GET:
        search = form.cleaned_data['search']
        businesses = timepiece.Business.objects.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
        if businesses.count() == 1:
            url_kwargs = {
                'business': businesses[0].pk,
            }
            return HttpResponseRedirect(
                reverse('view_business', kwargs=url_kwargs)
            )
    else:
        businesses = timepiece.Business.objects.all()

    context = {
        'form': form,
        'businesses': businesses,
    }
    return context


@permission_required('timepiece.view_business')
@render_with('timepiece/business/view.html')
def view_business(request, business):
    business = get_object_or_404(timepiece.Business, pk=business)
    context = {
        'business': business,
    }
    return context


@render_with('timepiece/business/create_edit.html')
def create_edit_business(request, business=None):
    if business:
        business = get_object_or_404(timepiece.Business, pk=business)
    if request.POST:
        business_form = timepiece_forms.BusinessForm(
            request.POST,
            instance=business,
        )
        if business_form.is_valid():
            business = business_form.save()
            return HttpResponseRedirect(
                reverse('view_business', args=(business.pk,))
            )
    else:
        business_form = timepiece_forms.BusinessForm(
            instance=business
        )
    context = {
        'business': business,
        'business_form': business_form,
    }
    return context


@permission_required('auth.view_user')
@render_with('timepiece/person/list.html')
def list_people(request):
    form = timepiece_forms.SearchForm(request.GET)
    if form.is_valid() and 'search' in request.GET:
        search = form.cleaned_data['search']
        people = auth_models.User.objects.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
        if people.count() == 1:
            url_kwargs = {
                'person_id': people[0].id,
            }
            return HttpResponseRedirect(
                reverse('view_person', kwargs=url_kwargs)
            )
    else:
        people = auth_models.User.objects.all().order_by('last_name')

    context = {
        'form': form,
        'people': people.select_related(),
    }
    return context


@permission_required('auth.view_user')
@transaction.commit_on_success
@render_with('timepiece/person/view.html')
def view_person(request, person_id):
    person = get_object_or_404(auth_models.User, pk=person_id)
    add_user_form = timepiece_forms.AddUserToProjectForm()
    context = {
        'person': person,
    }
    try:
        from ledger.models import Exchange
        context['exchanges'] = Exchange.objects.filter(
            transactions__project=project,
        ).distinct().select_related().order_by('type', '-date', '-id',)
        context['show_delivered_column'] = \
            context['exchanges'].filter(type__deliverable=True).count() > 0
    except ImportError:
        pass

    return context


@permission_required('auth.add_user')
@permission_required('auth.change_user')
@render_with('timepiece/person/create_edit.html')
def create_edit_person(request, person_id=None):
    if person_id:
        person = get_object_or_404(auth_models.User, pk=person_id)
    else:
        person = None
    if request.POST:
        if person:
            person_form = timepiece_forms.EditPersonForm(
                request.POST,
                instance=person,
            )
        else:
            person_form = timepiece_forms.CreatePersonForm(request.POST,)
        if person_form.is_valid():
            person = person_form.save()
            return HttpResponseRedirect(
                reverse('view_person', args=(person.id,))
            )
    else:
        if person:
            person_form = timepiece_forms.EditPersonForm(
                instance=person,
            )
        else:
            person_form = timepiece_forms.CreatePersonForm()

    context = {
        'person': person,
        'person_form': person_form,
    }
    return context


@permission_required('timepiece.view_project')
@render_with('timepiece/project/list.html')
def list_projects(request):
    form = timepiece_forms.SearchForm(request.GET)
    if form.is_valid() and 'search' in request.GET:
        search = form.cleaned_data['search']
        projects = timepiece.Project.objects.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
        if projects.count() == 1:
            url_kwargs = {
                'project_id': projects[0].id,
            }
            return HttpResponseRedirect(
                reverse('view_project', kwargs=url_kwargs)
            )
    else:
        projects = timepiece.Project.objects.all()

    context = {
        'form': form,
        'projects': projects.select_related('business'),
    }
    return context


@permission_required('timepiece.view_project')
@transaction.commit_on_success
@render_with('timepiece/project/view.html')
def view_project(request, project_id):
    project = get_object_or_404(timepiece.Project, pk=project_id)
    add_user_form = timepiece_forms.AddUserToProjectForm()
    context = {
        'project': project,
        'add_user_form': add_user_form,
    }
    try:
        from ledger.models import Exchange
        context['exchanges'] = Exchange.objects.filter(
            transactions__project=project,
        ).distinct().select_related().order_by('type', '-date', '-id',)
        context['show_delivered_column'] = \
            context['exchanges'].filter(type__deliverable=True).count() > 0
    except ImportError:
        pass

    return context


@csrf_exempt
@permission_required('timepiece.change_project')
@transaction.commit_on_success
def add_user_to_project(request, project_id):
    project = get_object_or_404(timepiece.Project, pk=project_id)
    if request.POST:
        form = timepiece_forms.AddUserToProjectForm(request.POST)
        if form.is_valid():
            user = form.save()
            timepiece.ProjectRelationship.objects.get_or_create(
                user=user,
                project=project,
            )
    if 'next' in request.REQUEST and request.REQUEST['next']:
        return HttpResponseRedirect(request.REQUEST['next'])
    else:
        return HttpResponseRedirect(
            reverse('view_project', args=(project.pk,)))


@csrf_exempt
@permission_required('timepiece.change_project')
@transaction.commit_on_success
def remove_user_from_project(request, project_id, user_id):
    project = get_object_or_404(timepiece.Project, pk=project_id)
    try:
        rel = timepiece.ProjectRelationship.objects.get(
            user=user_id,
            project=project,
        )
    except timepiece.ProjectRelationship.DoesNotExist:
        pass
    else:
        rel.delete()
    if 'next' in request.REQUEST and request.REQUEST['next']:
        return HttpResponseRedirect(request.REQUEST['next'])
    else:
        return HttpResponseRedirect(
            reverse('view_project', args=(project.pk,)))


@permission_required('timepiece.change_project')
@transaction.commit_on_success
@render_with('timepiece/project/relationship.html')
def edit_project_relationship(request, project_id, user_id):
    project = get_object_or_404(timepiece.Project, pk=project_id)
    try:
        rel = project.project_relationships.get(user__pk=user_id)
    except timepiece.ProjectRelationship.DoesNotExist:
        raise Http404
    rel = timepiece.ProjectRelationship.objects.get(
        project=project,
        user=rel.user,
    )
    if request.POST:
        relationship_form = timepiece_forms.ProjectRelationshipForm(
            request.POST,
            instance=rel,
        )
        if relationship_form.is_valid():
            rel = relationship_form.save()
            return HttpResponseRedirect(request.REQUEST['next'])
    else:
        relationship_form = \
            timepiece_forms.ProjectRelationshipForm(instance=rel)

    context = {
        'user': rel.user,
        'project': project,
        'relationship_form': relationship_form,
    }
    return context


@permission_required('timepiece.add_project')
@permission_required('timepiece.change_project')
@render_with('timepiece/project/create_edit.html')
def create_edit_project(request, project_id=None):
    project = get_object_or_404(timepiece.Project, pk=project_id) \
        if project_id else None
    form = timepiece_forms.ProjectForm(request.POST or None, instance=project)
    if request.POST and form.is_valid():
        project = form.save()
        project.save()
        return HttpResponseRedirect(
            reverse('view_project', args=(project.id,))
        )
    context = {
        'project': project,
        'project_form': form,
    }
    return context


@permission_required('timepiece.view_payroll_summary')
@render_with('timepiece/time-sheet/reports/summary.html')
def payroll_summary(request):
    year_month_form = timepiece_forms.YearMonthForm(request.GET or None)
    if request.GET and year_month_form.is_valid():
        from_date, to_date = year_month_form.save()
    else:
        from_date = utils.get_month_start(datetime.datetime.today()).date()
        to_date = from_date + relativedelta(months=1)
    last_billable = utils.get_last_billable_day(from_date)
    projects = getattr(settings, 'TIMEPIECE_PROJECTS', {})
    weekQ = Q(end_time__gt=utils.get_week_start(from_date),
              end_time__lt=last_billable + datetime.timedelta(days=1))
    monthQ = Q(end_time__gt=from_date, end_time__lt=to_date)
    workQ = ~Q(project__in=projects.values())
    statusQ = Q(status='invoiced') | Q(status='approved')
    # Weekly totals
    week_entries = timepiece.Entry.objects.date_trunc('week')
    week_entries = week_entries.filter(weekQ, statusQ, workQ)
    date_headers = utils.generate_dates(from_date, last_billable, by='week')
    weekly_totals = list(utils.project_totals(week_entries, date_headers,
                                              'total', overtime=True))
    # Monthly totals
    leave = timepiece.Entry.objects.filter(monthQ, ~workQ
                                  ).values('user', 'hours', 'project__name')
    month_entries = timepiece.Entry.objects.date_trunc('month')
    month_entries_valid = month_entries.filter(monthQ, statusQ, workQ)
    monthly_totals = list(utils.payroll_totals(month_entries_valid, from_date,
                                               leave))
    # Unapproved and unverified hours
    entries = timepiece.Entry.objects.filter(monthQ)
    user_values = ['user__pk', 'user__first_name', 'user__last_name']
    unverified = entries.filter(monthQ, status='unverified',
                                user__is_active=True)
    unapproved = entries.filter(monthQ, status='verified')
    return {
        'from_date': from_date,
        'year_month_form': year_month_form,
        'date_headers': date_headers,
        'weekly_totals': weekly_totals,
        'monthly_totals': monthly_totals,
        'unverified': unverified.values_list(*user_values).distinct(),
        'unapproved': unapproved.values_list(*user_values).distinct(),
    }


@permission_required('timepiece.view_projection_summary')
@render_with('timepiece/time-sheet/projection/projection.html')
@utils.date_filter
def projection_summary(request, form, from_date, to_date, status, activity):
    if not (from_date and to_date):
        today = datetime.date.today()
        from_date = today.replace(day=1)
        to_date = from_date + relativedelta(months=1)
    contracts = timepiece.ProjectContract.objects.exclude(status='complete')
    contracts = contracts.exclude(
        project__in=settings.TIMEPIECE_PROJECTS.values())
    contracts = contracts.order_by('end_date')
    users = User.objects.filter(assignments__contract__in=contracts).distinct()
    weeks = utils.generate_dates(start=from_date, end=to_date, by='week')

    return {
        'form': form,
        'weeks': weeks,
        'contracts': contracts.select_related(),
        'users': users,
    }


@login_required
@render_with('timepiece/person/settings.html')
def edit_settings(request):
    next_url = None
    if request.GET and 'next' in request.GET:
        next_url = request.GET['next']
        try:
            view_info = resolve(next_url)
        except Http404:
            next_url = None
    if not next_url:
        next_url = reverse('timepiece-entries')
    profile, created = timepiece.UserProfile.objects.get_or_create(
        user=request.user)
    if request.POST:
        user_form = timepiece_forms.UserForm(
            request.POST, instance=request.user)
        profile_form = timepiece_forms.UserProfileForm(
            request.POST, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.info(request, 'Your settings have been updated')
            return HttpResponseRedirect(next_url)
    else:
        profile_form = timepiece_forms.UserProfileForm(instance=profile)
        user_form = timepiece_forms.UserForm(instance=request.user)
    return {'profile_form': profile_form, 'user_form': user_form}


@permission_required('timepiece.view_payroll_summary')
@render_with('timepiece/time-sheet/reports/hourly.html')
@utils.date_filter
def hourly_report(request, date_form, from_date, to_date, status, activity):
    if not from_date:
        from_date = utils.get_month_start(datetime.datetime.today()).date()
    if not to_date:
        to_date = from_date + relativedelta(months=1)
    header_to = to_date - relativedelta(days=1)
    trunc = timepiece_forms.ProjectFiltersForm.DEFAULT_TRUNC
    query = Q(end_time__gt=utils.get_week_start(from_date),
              end_time__lt=to_date)
    if 'ok' in request.GET or 'export' in request.GET:
        form = timepiece_forms.ProjectFiltersForm(request.GET)
        if form.is_valid():
            trunc = form.cleaned_data['trunc']
            if not form.cleaned_data['paid_leave']:
                projects = getattr(settings, 'TIMEPIECE_PROJECTS', {})
                query &= ~Q(project__in=projects.values())
            if form.cleaned_data['pj_select']:
                query &= Q(project__in=form.cleaned_data['pj_select'])
    else:
        form = timepiece_forms.ProjectFiltersForm()
    hour_type = form.get_hour_type()
    entries = timepiece.Entry.objects.date_trunc(trunc).filter(query)
    date_headers = utils.generate_dates(from_date, header_to, by=trunc)
    project_totals = utils.project_totals(entries, date_headers, hour_type,
                                          total_column=True) if entries else ''
    if not request.GET.get('export', False):
        return {
            'date_form': date_form,
            'from_date': from_date,
            'date_headers': date_headers,
            'pj_filters': form,
            'trunc': trunc,
            'project_totals': project_totals,
        }
    else:
        from_date_str = from_date.strftime('%m-%d')
        to_date_str = to_date.strftime('%m-%d')
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = \
            'attachment; filename="%s_hours_%s_to_%s_by_%s.csv"' % (
            hour_type, from_date_str, to_date_str, trunc)
        writer = csv.writer(response)
        headers = ['Name']
        headers.extend([date.strftime('%m/%d/%Y') for date in date_headers])
        headers.append('Total')
        writer.writerow(headers)
        for rows, totals in project_totals:
            for name, hours in rows:
                data = [name]
                data.extend(hours)
                writer.writerow(data)
            total = ['Totals']
            total.extend(totals)
            writer.writerow(total)
        return response


class ContractDetail(DetailView):
    template_name = 'timepiece/time-sheet/contract/view.html'
    model = timepiece.ProjectContract
    context_object_name = 'contract'

    @method_decorator(permission_required('timepiece.add_project_contract'))
    def dispatch(self, *args, **kwargs):
        return super(ContractDetail, self).dispatch(*args, **kwargs)


class ContractList(ListView):
    template_name = 'timepiece/time-sheet/contract/list.html'
    model = timepiece.ProjectContract
    context_object_name = 'contracts'
    queryset = timepiece.ProjectContract.objects.filter(
        status='current'
    ).select_related(
        'project'
    ).order_by(
        'project__name'
    )

    @method_decorator(permission_required('timepiece.add_project_contract'))
    def dispatch(self, *args, **kwargs):
        return super(ContractList, self).dispatch(*args, **kwargs)
