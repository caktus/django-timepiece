import csv
import datetime

from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Sum, Q
from django.db import transaction

from crm.decorators import render_with
from crm import forms as crm_forms
from crm import models as crm

from timepiece import models as timepiece 
from timepiece.utils import determine_period
from timepiece import forms as timepiece_forms
from timepiece.templatetags.timepiece_tags import seconds_to_hours


@login_required
@render_with('timepiece/entry/list.html')
def view_entries(request):
    two_weeks_ago = datetime.date.today() - datetime.timedelta(days=14)
    entries = timepiece.Entry.objects.select_related(
        'project__business',
    ).filter(
        user=request.user,
        start_time__gte=two_weeks_ago,
    )
    project_entries = entries.values(
        'project__name',
    ).annotate(sum=Sum('hours')).order_by('-sum')
    activity_entries = entries.values(
        'activity__name',
    ).annotate(sum=Sum('hours')).order_by('-sum')
    context = {
        'entries': entries.order_by('-start_time'),
        'project_entries': project_entries,
        'activity_entries': activity_entries,
    }
    return context


@permission_required('timepiece.can_clock_in')
@transaction.commit_on_success
def clock_in(request):
    if request.POST:
        form = timepiece_forms.ClockInForm(request.POST)
        if form.is_valid():
            # if the user chose to pause any open entries, pause them
            if request.POST.get('pause_open', '0') == '1':
                open_entries = timepiece.Entry.objects.filter(
                    user=request.user,
                    end_time__isnull=True,
                    pause_time__isnull=True,
                )
                for log in open_entries:
                    log.pause()
                    log.save()
            entry = form.save(user=request.user)
            request.user.message_set.create(message='You have clocked into %s' % entry.project)
            return HttpResponseRedirect(reverse('timepiece-entries'))
        else:
            request.user.message_set.create(message='Please correct the errors below.')
    else:
        form = timepiece_forms.ClockInForm()
    return render_to_response(
        'timepiece/clock_in.html',
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
        'timepiece/clock_out.html',
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

        # create a message that can be displayed to the user
        request.user.message_set.create(message='The log entry has been %s.' % action)

    # redirect to the log entry list
    return HttpResponseRedirect(reverse('timepiece-entries'))

@permission_required('timepiece.change_entry')
def update_entry(request, entry_id):
    """
    Give the user the ability to update their closed entries.  If this method
    is invoked via a GET request, the user is presented with a form that is
    populated with the entry's original data.  If this method is invoked via a
    POST request, the data the user entered in the form will be validated.  If
    the data are valid, the entry will be updated accordingly.  If the data are
    invalid, the user is presented with the form again, either until they abort
    or enter valid data.
    """

    try:
        # retrieve the log entry
        entry = timepiece.Entry.objects.get(pk=entry_id,
                                  user=request.user,
                                  end_time__isnull=False)
    except:
        # entry does not exist
        request.user.message_set.create(message='No such log entry.')
        return HttpResponseRedirect(reverse('timepiece-entries'))

    if request.method == 'POST':
        # populate the form with the updated data
        form = timepiece_forms.AddUpdateEntryForm(request.POST, instance=entry)

        # validate the form data
        if form.is_valid():
            # the data are valid... save them
            form.save()

            # create a message for the user
            request.user.message_set.create(message='The entry has been updated successfully.')

            # redirect them to the log entry list
            return HttpResponseRedirect(reverse('timepiece-entries'))
        else:
            # create an error message
            request.user.message_set.create(message='Please fix the errors below.')
    else:
        # populate the form with the original entry information
        form = timepiece_forms.AddUpdateEntryForm(instance=entry)

    return render_to_response('timepiece/add_update_entry.html',
                              {'form': form,
                               'add_update': 'Update',
                               'callback': reverse('timepiece-update', args=[entry_id])},
                              context_instance=RequestContext(request))

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

    return render_to_response('timepiece/delete_entry.html',
                              {'entry': entry},
                              context_instance=RequestContext(request))

@permission_required('timepiece.add_entry')
def add_entry(request):
    """
    Give users a way to add entries in the past.  This is beneficial if the
    website goes down or there is no connectivity for whatever reason.  When
    this method is invoked via a GET request, the user is presented with an
    empty form, which is then posted back to this method.  When this method
    is invoked via a POST request, the form data are validated.  If the data
    are valid, they will be saved as a new entry, and the user will be sent
    back to their log entry list.  If the data are invalid, the user will see
    the form again with the information they entered until they either abort
    or enter valid data.
    """

    if request.method == 'POST':
        # populate the form with the posted data
        form = timepiece_forms.AddUpdateEntryForm(request.POST)

        # validate the data
        if form.is_valid():
            # the data are valid... save them
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()

            # create a message for the user
            request.user.message_set.create(message='The entry has been added successfully.')

            # redirect them to the log entry list
            return HttpResponseRedirect(reverse('timepiece-entries'))
        else:
            # create an error message for the user to see
            request.user.message_set.create(message='Please correct the errors below')
    else:
        # send back an empty form
        form = timepiece_forms.AddUpdateEntryForm()

    return render_to_response('timepiece/add_update_entry.html',
                              {'form': form,
                               'add_update': 'Add',
                               'callback': reverse('timepiece-add')},
                              context_instance=RequestContext(request))


@permission_required('timepiece.view_entry_summary')
@render_with('timepiece/entry/summary.html')
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
    project_totals = entries.filter(dates).annotate(hours=Sum('hours'))
    total_hours = timepiece.Entry.objects.filter(dates).aggregate(
        hours=Sum('hours')
    )['hours']
    context = {
        'form': form,
        'project_totals': project_totals,
        'total_hours': total_hours,
    }
    return context


def get_project_entries(project, window_id=None):
    """
    Returns a tuple of the billing window, corresponding entries, and total 
    hours for the given project and window_id, if specified.
    """
    window = timepiece.BillingWindow.objects.select_related('period')
    if window_id:
        window = window.get(
            pk=window_id,
            period__active=True,
            period=project.billing_period,
        )
    else:
        window = window.filter(
            period__active=True,
            period=project.billing_period,
        ).order_by('-date')[0]
    entries = timepiece.Entry.objects.filter(
        project=project,
        start_time__gte=window.date,
        end_time__lt=window.end_date,
    ).select_related(
        'user',
    ).order_by('start_time')
    total = entries.aggregate(hours=Sum('hours'))['hours']
    return window, entries, total


@permission_required('timepiece.view_project_time_sheet')
@render_with('timepiece/period/window.html')
def project_time_sheet(request, project, window_id=None):
    window, entries, total = get_project_entries(project, window_id)
    user_entries = entries.order_by().values(
        'user__username',
    ).annotate(sum=Sum('hours')).order_by('-sum')
    activity_entries = entries.order_by().values(
        'activity__name',
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
    window, entries, total = get_project_entries(project, window_id)
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
def view_project(request, business, project):
    add_contact_form = crm_forms.AssociateContactForm()
    context = {
        'project': project,
        'add_contact_form': add_contact_form,
        'repeat_period': project.billing_period,
    }
    try:
        from ledger.models import Exchange
        context['exchanges'] = Exchange.objects.filter(
            business=business,
            transactions__project=project,
        ).distinct().select_related().order_by('type', '-date', '-id',)
        context['show_delivered_column'] = \
            context['exchanges'].filter(type__deliverable=True).count() > 0
    except ImportError:
        pass

    return context


@permission_required('timepiece.change_project')
@transaction.commit_on_success
@render_with('timepiece/project/relationship.html')
def edit_project_relationship(request, business, project, user_id):
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
def create_edit_project(request, business, project=None):
    if project:
        billing_period = project.billing_period
    else:
        billing_period = None
    if request.POST:
        project_form = timepiece_forms.ProjectForm(
            request.POST,
            business=business,
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
                reverse('view_project', args=(business.id, project.id))
            )
    else:
        project_form = timepiece_forms.ProjectForm(
            business=business, 
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
        'business': business,
        'project': project,
        'project_form': project_form,
        'repeat_period_form': repeat_period_form,
        'latest_window': latest_window,
    }
    return context
