from django.template import RequestContext
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.sites.models import Site
from pendulum.forms import ClockInForm, ClockOutForm, AddUpdateEntryForm
from pendulum.models import Entry
from pendulum.utils import determine_period
from datetime import datetime

@login_required
def view_entries(request, delta=0):
    """
    Pull back a list of all entries for the current period for the current user
    """
    delta = int(delta)

    if delta:
        # we only go back in time, not forward :)
        if delta < 0: raise Http404

        # we have a delta, so show previous entries according to the delta
        entries = Entry.objects.previous(delta, request.user)
        next = delta - 1
        has_next = True
    else:
        # no delta, so just show the current entries
        entries = Entry.objects.current(request.user)
        next = None
        has_next = False

    return render_to_response('pendulum/entry_list.html',
                              {'entries': entries,
                               'period': determine_period(delta=delta),
                               'is_current': delta != 0,
                               'next_period': next,
                               'has_next': has_next,
                               'previous_period': delta + 1},
                              context_instance=RequestContext(request))

@permission_required('pendulum.can_clock_in')
def clock_in(request):
    """
    Let a user clock in.  If this method is called via a GET request, a blank
    form is displayed to the user which has a single field where they choose
    the project they will be working on.  If the method is invoked via a POST
    request, the posted form data are validated.  If the data are valid, a new
    log entry is created and the user is redirected to the entry list.  If the
    data are invalid, the user is presented with the same form until they abort
    or enter valid data.
    """

    if request.method == 'POST':
        # populate the form with the posted values
        form = ClockInForm(request.POST)

        # validate the form data
        if form.is_valid():
            # the form is valid, so create the new entry
            e = Entry()
            e.clock_in(request.user, form.cleaned_data['project'])

            # if the user chose to pause any open entries, pause them
            if request.POST.get('pause_open', '0') == '1':
                open = Entry.objects.current().filter(user=request.user,
                                                      end_time__isnull=True,
                                                      pause_time__isnull=True)
                for log in open:
                    log.pause()
                    log.save()

            e.save()

            # create a message that may be displayed to the user
            request.user.message_set.create(message='You have clocked into %s' % e.project)
            return HttpResponseRedirect(reverse('pendulum-entries'))
        else:
            # show an error message
            request.user.message_set.create(message='Please correct the errors below.')
    else:
        # send back an empty form
        form = ClockInForm()

    return render_to_response('pendulum/clock_in.html',
                              {'form': form},
                              context_instance=RequestContext(request))

@permission_required('pendulum.can_clock_out')
def clock_out(request, entry_id):
    """
    Allow a user to clock out or close a log entry.  If this method is invoked
    via a GET request, the user is presented with a form that allows them to
    select an activity type and enter comments about their activities.  Only
    the activity is required.  If this method is invoked via a POST request,
    the form is validated.  If the form data are valid, the entry is closed and
    the user is redirected to the entry list.  If the form data are invalid,
    the user is presented with the form again until they abort or they enter
    valid data.
    """

    try:
        # grab the entry from the database
        entry = Entry.objects.get(pk=entry_id,
                                  user=request.user,
                                  end_time__isnull=True)
    except:
        # if this entry does not exist, redirect to the entry list
        request.user.message_set.create(message='Invalid log entry.')
        return HttpResponseRedirect(reverse('pendulum-entries'))

    if request.method == 'POST':
        # populate the form with the posted data
        form = ClockOutForm(request.POST)

        # validate the form data
        if form.is_valid():
            # the form is valid, save the entry
            entry.clock_out(form.cleaned_data['activity'],
                            form.cleaned_data['comments'])
            entry.save()

            # create a message to show to the user
            request.user.message_set.create(message="You've been clocked out.")
            return HttpResponseRedirect(reverse('pendulum-entries'))
        else:
            # create an error message for the user
            request.user.message_set.create(message="Invalid entry!")
    else:
        # send back an empty form
        form = ClockOutForm()

    return render_to_response('pendulum/clock_out.html',
                              {'form': form,
                               'entry': entry},
                              context_instance=RequestContext(request))

@permission_required('pendulum.can_pause')
def toggle_paused(request, entry_id):
    """
    Allow the user to pause and unpause their open entries.  If this method is
    invoked on an entry that is not paused, it will become paused.  If this
    method is invoked on an entry that is already paused, it will unpause it.
    Then the user will be redirected to their log entry list.
    """

    try:
        # retrieve the log entry
        entry = Entry.objects.get(pk=entry_id,
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
    return HttpResponseRedirect(reverse('pendulum-entries'))

@permission_required('pendulum.change_entry')
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
        entry = Entry.objects.get(pk=entry_id,
                                  user=request.user,
                                  end_time__isnull=False)
    except:
        # entry does not exist
        request.user.message_set.create(message='No such log entry.')
        return HttpResponseRedirect(reverse('pendulum-entries'))

    if request.method == 'POST':
        # populate the form with the updated data
        form = AddUpdateEntryForm(request.POST, instance=entry)

        # validate the form data
        if form.is_valid():
            # the data are valid... save them
            form.save()

            # create a message for the user
            request.user.message_set.create(message='The entry has been updated successfully.')

            # redirect them to the log entry list
            return HttpResponseRedirect(reverse('pendulum-entries'))
        else:
            # create an error message
            request.user.message_set.create(message='Please fix the errors below.')
    else:
        # populate the form with the original entry information
        form = AddUpdateEntryForm(instance=entry)

    return render_to_response('pendulum/add_update_entry.html',
                              {'form': form,
                               'add_update': 'Update',
                               'callback': reverse('pendulum-update', args=[entry_id])},
                              context_instance=RequestContext(request))

@permission_required('pendulum.delete_entry')
def delete_entry(request, entry_id):
    """
    Give the user the ability to delete a log entry, with a confirmation
    beforehand.  If this method is invoked via a GET request, a form asking
    for a confirmation of intent will be presented to the user.  If this method
    is invoked via a POST request, the entry will be deleted.
    """

    try:
        # retrieve the log entry
        entry = Entry.objects.get(pk=entry_id,
                                  user=request.user)
    except:
        # entry does not exist
        request.user.message_set.create(message='No such log entry.')
        return HttpResponseRedirect(reverse('pendulum-entries'))

    if request.method == 'POST':
        key = request.POST.get('key', None)
        if key and key == entry.delete_key:
            entry.delete()
            request.user.message_set.create(message='Entry deleted.')
            return HttpResponseRedirect(reverse('pendulum-entries'))
        else:
            request.user.message_set.create(message='You do not appear to be authorized to delete this entry!')

    return render_to_response('pendulum/delete_entry.html',
                              {'entry': entry},
                              context_instance=RequestContext(request))

@permission_required('pendulum.add_entry')
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
        form = AddUpdateEntryForm(request.POST)

        # validate the data
        if form.is_valid():
            # the data are valid... save them
            entry = form.save(commit=False)
            entry.user = request.user
            entry.site = Site.objects.get_current()
            entry.save()

            # create a message for the user
            request.user.message_set.create(message='The entry has been added successfully.')

            # redirect them to the log entry list
            return HttpResponseRedirect(reverse('pendulum-entries'))
        else:
            # create an error message for the user to see
            request.user.message_set.create(message='Please correct the errors below')
    else:
        # send back an empty form
        form = AddUpdateEntryForm()

    return render_to_response('pendulum/add_update_entry.html',
                              {'form': form,
                               'add_update': 'Add',
                               'callback': reverse('pendulum-add')},
                              context_instance=RequestContext(request))
