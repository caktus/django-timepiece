import csv
import datetime
import calendar
import math
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from dateutil import rrule

from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseForbidden
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.db.models import Sum, Q, F
from django.db import transaction
from django.conf import settings
from django.utils.datastructures import SortedDict
from django.views.decorators.csrf import csrf_exempt

from timepiece.utils import render_with
from crm import forms as crm_forms
from crm import models as crm

from timepiece import models as timepiece
from timepiece import utils
from timepiece import forms as timepiece_forms
from timepiece.templatetags.timepiece_tags import seconds_to_hours

try:
    settings.TIMEPIECE_TIMESHEET_EDITABLE_DAYS
except AttributeError:
    settings.TIMEPIECE_TIMESHEET_EDITABLE_DAYS = 3

@login_required
@render_with('timepiece/time-sheet/dashboard.html')
def view_entries(request):
    week_start = utils.get_week_start()
    entries = timepiece.Entry.objects.select_related(
        'project__business',
    ).filter(
        user=request.user,
        end_time__gte=week_start,
    )
    today = datetime.date.today()
    assignments = timepiece.ContractAssignment.objects.filter(
        contact=request.user,
        contact__project_relationships__project=F('contract__project'),
        end_date__gte=today,
        contract__status='current',
    ).order_by('contract__project__type', 'end_date')
    project_entries = entries.values(
        'project__name',
    ).annotate(sum=Sum('hours')).order_by('-sum')
    activity_entries = entries.values(
        'billable',
    ).annotate(sum=Sum('hours')).order_by('-sum')
    others_active_entries = timepiece.Entry.objects.filter(
        end_time__isnull=True,
    ).exclude(
        user=request.user,
    )
    my_active_entries = timepiece.Entry.objects.select_related(
        'project__business',
    ).filter(
        user=request.user,
        end_time__isnull=True,
    )
    allocations = timepiece.AssignmentAllocation.objects.during_this_week(
        request.user
        ).order_by('assignment__contract__project__name')
    allocated_projects = allocations.values_list('assignment__contract__project',)
    project_entries = entries.exclude(
        project__in=allocated_projects,
    ).values(
        'project__name', 'project__pk'
    ).annotate(sum=Sum('hours')).order_by('project__name')
    schedule = timepiece.PersonSchedule.objects.filter(
                                    contact__in=request.user.contacts.all())
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
    if request.POST:
        form = timepiece_forms.ClockInForm(request.POST, user=request.user)
        if form.is_valid():
            # if the user chose to pause any open entries, pause them
            entry = form.save()
            request.user.message_set.create(message='You have clocked into %s' % entry.project)
            return HttpResponseRedirect(reverse('timepiece-entries'))
        else:
            request.user.message_set.create(message='Please correct the errors below.')
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
        entry = timepiece.Entry.objects.get(pk=entry_id,
                                  user=request.user,
                                  end_time__isnull=True)
    except:
        # create an error message for the user
        request.user.message_set.create(message='The entry could not be paused.  Please try again.')
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
            entry = timepiece.Entry.objects.get(
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
        entry = timepiece.Entry.objects.get(pk=entry_id,
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
            request.user.message_set.create(message='You do not appear to be authorized to delete this entry!')

    return render_to_response('timepiece/time-sheet/entry/delete_entry.html',
                              {'entry': entry},
                              context_instance=RequestContext(request))


@permission_required('timepiece.view_entry_summary')
@render_with('timepiece/time-sheet/general_ledger.html')
def summary(request, username=None):
    if request.GET:
        form = timepiece_forms.DateForm(request.GET)
        if form.is_valid():
            from_date, to_date = form.save()
    else:
        form = timepiece_forms.DateForm()
        from_date, to_date = None, None
    entries = timepiece.Entry.objects.values(
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
    total_hours = timepiece.Entry.objects.filter(dates).aggregate(
        hours=Sum('hours')
    )['hours']
    people_totals = timepiece.Entry.objects.values('user', 'user__first_name',
                                                   'user__last_name')
    people_totals = people_totals.order_by('user').filter(dates)
    people_totals = people_totals.annotate(total_hours=Sum('hours'))
    context = {
        'form': form,
        'project_totals': project_totals,
        'total_hours': total_hours,
        'people_totals': people_totals,
    }
    return context


def get_entries(period, window_id=None, project=None, user=None):
    """
    Returns a tuple of the billing window, corresponding entries, and total
    hours for the given project and window_id, if specified.
    """
    if not project and not user:
        raise ValueError('project or user required')
    window = timepiece.BillingWindow.objects.select_related('period')
    if window_id:
        window = window.get(
            pk=window_id,
            period__active=True,
            period=period,
        )
    else:
        window = window.filter(
            period__active=True,
            period=period,
        ).order_by('-date')[0]
    entries = timepiece.Entry.objects.filter(
        end_time__gte=window.date,
        end_time__lt=window.end_date,
    ).select_related(
        'user',
    ).order_by('start_time')
    if project:
        entries = entries.filter(project=project)
    elif user:
        entries = entries.filter(user=user)
    total = entries.aggregate(hours=Sum('hours'))['hours']
    return window, entries, total


@permission_required('timepiece.view_project_time_sheet')
@render_with('timepiece/time-sheet/projects/view.html')
def project_time_sheet(request, project, window_id=None):
    window, entries, total = get_entries(
        project.billing_period,
        window_id=window_id,
        project=project,
    )
    user_entries = entries.order_by().values(
        'user__username',
        'user__first_name',
        'user__last_name',
    ).annotate(sum=Sum('hours')).order_by('-sum')
    activity_entries = entries.order_by().values(
        'billable',
    ).annotate(sum=Sum('hours')).order_by('-sum')
    context = {
        'project': project,
        'period': window.period,
        'window': window,
        'entries': entries,
        'total': total,
        'user_entries': user_entries,
        'activity_entries': activity_entries,
    }
    return context


@permission_required('timepiece.export_project_time_sheet')
def export_project_time_sheet(request, project, window_id=None):
    window, entries, total = get_entries(
        project.billing_period,
        window_id=window_id,
        project=project,
    )
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s Timesheet %s.csv"' % (project.name, window.end_date.strftime('%Y-%m-%d'))
    writer = csv.writer(response)
    writer.writerow((
        'Date',
        'Weekday',
        'Developer',
        'Location',
        'Time In',
        'Time Out',
        'Breaks',
        'Hours',
    ))
    for entry in entries:
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
        writer.writerow(data)
    writer.writerow(('', '', '', '', '', '', 'Total:', total))
    return response

@login_required
@render_with('timepiece/time-sheet/people/view.html')
def view_person_time_sheet(request, person_id, period_id, window_id=None):
    try:
        time_sheet = timepiece.PersonRepeatPeriod.objects.select_related(
            'contact',
            'repeat_period',
        ).get(
            contact__id=person_id,
            repeat_period__id=period_id,
        )
    except timepiece.PersonRepeatPeriod.DoesNotExist:
        raise Http404
    if not (request.user.has_perm('timepiece.view_person_time_sheet') or \
    time_sheet.contact.pk == request.user.pk):
        return HttpResponseForbidden('Forbidden')
    window, entries, total = get_entries(
        time_sheet.repeat_period,
        window_id=window_id,
        user=time_sheet.contact,
    )
    project_entries = entries.order_by().values(
        'project__name',
    ).annotate(sum=Sum('hours')).order_by('-sum')
    activity_entries = entries.order_by().values(
        'billable',
    ).annotate(sum=Sum('hours')).order_by('-sum')
    is_editable = window.end_date +\
        datetime.timedelta(days=settings.TIMEPIECE_TIMESHEET_EDITABLE_DAYS) >=\
        datetime.date.today()


    context = {
        'is_editable': is_editable,
        'person': time_sheet.contact,
        'period': window.period,
        'window': window,
        'entries': entries,
        'total': total,
        'project_entries': project_entries,
        'activity_entries': activity_entries,
    }
    return context


@permission_required('timepiece.view_project')
@render_with('timepiece/project/list.html')
def list_projects(request):
    form = crm_forms.SearchForm(request.GET)
    if form.is_valid() and 'search' in request.GET:
        search = form.cleaned_data['search']
        projects = timepiece.Project.objects.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
        if projects.count() == 1:
            url_kwargs = {
                'business_id': projects[0].business.id,
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
def view_project(request, project):
    add_contact_form = timepiece_forms.AddContactToProjectForm()
    context = {
        'project': project,
        'add_contact_form': add_contact_form,
        'repeat_period': project.billing_period,
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
def add_contact_to_project(request, project):
    if request.POST:
        form = timepiece_forms.AddContactToProjectForm(request.POST)
        if form.is_valid():
            contact = form.save()
            timepiece.ProjectRelationship.objects.get_or_create(
                contact=contact,
                project=project,
            )
    if 'next' in request.REQUEST and request.REQUEST['next']:
        return HttpResponseRedirect(request.REQUEST['next'])
    else:
        return HttpResponseRedirect(reverse('view_project', project,))


@csrf_exempt
@permission_required('timepiece.change_project')
@transaction.commit_on_success
def remove_contact_from_project(request, project, contact_id):        
    try:
        rel = timepiece.ProjectRelationship.objects.get(
            contact=contact_id,
            project=project,
        )
    except timepiece.ProjectRelationship.DoesNotExist:
        pass
    else:
        rel.delete()
    if 'next' in request.REQUEST and request.REQUEST['next']:
        return HttpResponseRedirect(request.REQUEST['next'])
    else:
        return HttpResponseRedirect(reverse('view_project', project,))


@permission_required('timepiece.change_project')
@transaction.commit_on_success
@render_with('timepiece/project/relationship.html')
def edit_project_relationship(request, project, user_id):
    try:
        rel = project.project_relationships.get(contact__pk=user_id)
    except timepiece.ProjectRelationship.DoesNotExist:
        raise Http404
    rel = timepiece.ProjectRelationship.objects.get(
        project=project,
        contact=rel.contact,
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
        'user': rel.contact,
        'project': project,
        'relationship_form': relationship_form,
    }
    return context


@permission_required('timepiece.add_project')
@permission_required('timepiece.change_project')
@render_with('timepiece/project/create_edit.html')
def create_edit_project(request, project=None):
    if project:
        billing_period = project.billing_period
    else:
        billing_period = None
    if request.POST:
        project_form = timepiece_forms.ProjectForm(
            request.POST,
            instance=project,
        )
        repeat_period_form = timepiece_forms.RepeatPeriodForm(
            request.POST,
            instance=billing_period,
            prefix='repeat',
        )
        if project_form.is_valid() and repeat_period_form.is_valid():
            period = repeat_period_form.save()
            project = project_form.save()
            project.billing_period = period
            project.save()
            return HttpResponseRedirect(
                reverse('view_project', args=(project.id,))
            )
    else:
        project_form = timepiece_forms.ProjectForm(
            instance=project
        )
        repeat_period_form = timepiece_forms.RepeatPeriodForm(
            instance=billing_period,
            prefix='repeat',
        )

    if billing_period:
        latest_window = project.billing_period.billing_windows.latest()
    else:
        latest_window = None

    context = {
        'project': project,
        'project_form': project_form,
        'repeat_period_form': repeat_period_form,
        'latest_window': latest_window,
    }
    return context


@permission_required('timepiece.view_project_time_sheet')
@render_with('timepiece/time-sheet/projects/list.html')
def tracked_projects(request):
    time_sheets = timepiece.Entry.objects.filter(
        project__billing_period__active=True,
    ).values(
        'project__name',
        'project__business__name',
        'project__id',
        'project__business__id',
    ).annotate(
        total_hours=Sum('hours'),
    ).order_by('project__name')
    return {
        'time_sheets': time_sheets,
    }


@permission_required('timepiece.view_person_time_sheet')
@render_with('timepiece/time-sheet/people/list.html')
def tracked_people(request):
    time_sheets = timepiece.PersonRepeatPeriod.objects.select_related(
        'contact',
        'repeat_period',
    ).filter(
        repeat_period__active=True,
    ).order_by(
        'contact__last_name',
    )
    return {
        'time_sheets': time_sheets,
    }


@permission_required('timepiece.view_project_time_sheet')
@transaction.commit_on_success
@render_with('timepiece/time-sheet/people/create_edit.html')
def create_edit_person_time_sheet(request, person_id=None):
    if person_id:
        try:
            time_sheet = timepiece.PersonRepeatPeriod.objects.select_related(
                'contact',
                'repeat_period',
            ).get(contact__id=person_id)
        except timepiece.PersonRepeatPeriod.DoesNotExist:
            raise Http404
        person = time_sheet.contact
        repeat_period = time_sheet.repeat_period
        latest_window = repeat_period.billing_windows.latest()
    else:
        person = None
        time_sheet = None
        repeat_period = None
        latest_window = None

    if request.POST:
        form = timepiece_forms.PersonTimeSheet(
            request.POST,
            instance=time_sheet,
        )
        repeat_period_form = timepiece_forms.RepeatPeriodForm(
            request.POST,
            instance=repeat_period,
        )
        if form.is_valid() and repeat_period_form.is_valid():
            repeat_period = repeat_period_form.save()
            person_time_sheet = form.save(commit=False)
            person_time_sheet.repeat_period = repeat_period
            person_time_sheet.save()
            return HttpResponseRedirect(reverse('tracked_people'))
    else:
        form = timepiece_forms.PersonTimeSheet(instance=time_sheet)
        repeat_period_form = timepiece_forms.RepeatPeriodForm(
            instance=repeat_period,
        )

    return {
        'form': form,
        'person': person,
        'repeat_period_form': repeat_period_form,
        'latest_window': latest_window,
    }


@permission_required('timepiece.view_payroll_summary')
@render_with('timepiece/time-sheet/payroll/summary.html')
def payroll_summary(request):
    if request.GET:
        form = timepiece_forms.DateForm(request.GET)
        if form.is_valid():
            from_date, to_date = form.save()
    else:
        form = timepiece_forms.DateForm()
        today = datetime.date.today()
        from_date = today.replace(day=1)
        to_date = from_date + relativedelta(months=1)

    project_totals = timepiece.Entry.objects.filter(
        end_time__lt=to_date,
        end_time__gte=from_date,
    ).values('project__name', 'billable').annotate(s=Sum('hours')).order_by('project__name')
    projects = SortedDict()
    for row in project_totals:
        name = row['project__name']
        billable = row['billable']
        hours = row['s']
        if name not in projects:
            projects[name] = {}
        if billable:
            projects[name]['billable'] = hours
        else:
            projects[name]['non_billable'] = hours

    all_weeks = utils.generate_weeks(start=from_date, end=to_date)
    rps = timepiece.PersonRepeatPeriod.objects.select_related(
        'contact',
        'repeat_period',
    ).filter(
        repeat_period__active=True,
    ).order_by('contact__last_name')
    for rp in rps:
        rp.contact.summary = rp.summary(from_date, to_date)

    cals = []
    date = from_date - relativedelta(months=1)
    end_date = from_date + relativedelta(months=1)
    html_cal = calendar.HTMLCalendar(calendar.SUNDAY)
    while date < end_date:
        cals.append(html_cal.formatmonth(date.year, date.month))
        date += relativedelta(months=1)

    return {
        'form': form,
        'all_weeks': all_weeks,
        'cals': cals,
        'projects': projects,
        'periods': rps,
        'to_date': to_date,
        'from_date': from_date,
    }


@permission_required('timepiece.view_projection_summary')
@render_with('timepiece/time-sheet/projection/projection.html')
def projection_summary(request):
    contracts = timepiece.ProjectContract.objects.exclude(status='complete')
    contracts = contracts.exclude(project__in=settings.TIMEPIECE_PROJECTS.values())
    contracts = contracts.order_by('end_date')
    contacts = User.objects.filter(assignments__contract__in=contracts).distinct()

    if request.GET:
        form = timepiece_forms.DateForm(request.GET)
        if form.is_valid():
            from_date, to_date = form.save()
    else:
        form = timepiece_forms.DateForm()
        from_date = datetime.date.today()
        #from_date = today.replace(day=1)
        to_date = from_date + relativedelta(months=3)

    weeks = utils.generate_weeks(start=from_date, end=to_date)

    return {
        'form': form,
        'weeks': weeks,
        'contracts': contracts,
        'contacts': contacts,
    }

