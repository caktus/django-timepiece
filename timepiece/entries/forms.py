import datetime
from dateutil.relativedelta import relativedelta

from django import forms
from django.db.models import Q

from selectable import forms as selectable

from timepiece import utils
from timepiece.crm.models import Project, ProjectRelationship
from timepiece.entries.models import Entry, Location, ProjectHours
from timepiece.entries.lookups import ActivityLookup
from timepiece.forms import (
    INPUT_FORMATS, TimepieceSplitDateTimeField, TimepieceDateInput)


class ClockInForm(forms.ModelForm):
    active_comment = forms.CharField(
        label='Notes for the active entry', widget=forms.Textarea,
        required=False)
    start_time = TimepieceSplitDateTimeField(required=False)

    class Meta:
        model = Entry
        fields = ('active_comment', 'location', 'project', 'activity',
                  'start_time', 'comments')
        widgets = {
            'activity': selectable.AutoComboboxSelectWidget(lookup_class=ActivityLookup),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.active = kwargs.pop('active', None)

        initial = kwargs.get('initial', {})
        default_loc = utils.get_setting('TIMEPIECE_DEFAULT_LOCATION_SLUG')
        if default_loc:
            try:
                loc = Location.objects.get(slug=default_loc)
            except Location.DoesNotExist:
                loc = None
            if loc:
                initial['location'] = loc.pk
        project = initial.get('project', None)
        try:
            last_project_entry = Entry.objects.filter(
                user=self.user, project=project).order_by('-end_time')[0]
        except IndexError:
            initial['activity'] = None
        else:
            initial['activity'] = last_project_entry.activity.pk

        super(ClockInForm, self).__init__(*args, **kwargs)

        self.fields['start_time'].initial = datetime.datetime.now()
        self.fields['project'].queryset = Project.trackable.filter(
            users=self.user)
        if not self.active:
            self.fields.pop('active_comment')
        else:
            self.fields['active_comment'].initial = self.active.comments
        self.instance.user = self.user

    def clean_start_time(self):
        """
        Make sure that the start time doesn't come before the active entry
        """
        start = self.cleaned_data.get('start_time')
        if not start:
            return start
        active_entries = self.user.timepiece_entries.filter(
            start_time__gte=start, end_time__isnull=True)
        for entry in active_entries:
            output = ('The start time is on or before the current entry: '
                      '%s - %s starting at %s' % (entry.project, entry.activity,
                                                  entry.start_time.strftime('%H:%M:%S')))
            raise forms.ValidationError(output)
        return start

    def clean(self):
        start_time = self.clean_start_time()
        data = self.cleaned_data
        if not start_time:
            return data
        if self.active:
            self.active.unpause()
            self.active.comments = data['active_comment']
            self.active.end_time = start_time - relativedelta(seconds=1)
            if not self.active.clean():
                raise forms.ValidationError(data)
        return data

    def save(self, commit=True):
        self.instance.hours = 0
        entry = super(ClockInForm, self).save(commit=commit)
        if self.active and commit:
            self.active.save()
        return entry


class ClockOutForm(forms.ModelForm):
    start_time = TimepieceSplitDateTimeField()
    end_time = TimepieceSplitDateTimeField()

    class Meta:
        model = Entry
        fields = ('location', 'start_time', 'end_time', 'comments')

    def __init__(self, *args, **kwargs):
        kwargs['initial'] = kwargs.get('initial', None) or {}
        kwargs['initial']['end_time'] = datetime.datetime.now()
        super(ClockOutForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        entry = super(ClockOutForm, self).save(commit=False)
        entry.unpause(entry.end_time)
        if commit:
            entry.save()
        return entry


class AddUpdateEntryForm(forms.ModelForm):
    start_time = TimepieceSplitDateTimeField()
    end_time = TimepieceSplitDateTimeField()

    class Meta:
        model = Entry
        exclude = ('user', 'pause_time', 'site', 'hours', 'status',
                   'entry_group')
        widgets = {
            'activity': selectable.AutoComboboxSelectWidget(lookup_class=ActivityLookup),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.acting_user = kwargs.pop('acting_user')
        super(AddUpdateEntryForm, self).__init__(*args, **kwargs)
        self.instance.user = self.user
        self.fields['project'].queryset = Project.trackable.filter(
            users=self.user)
        # If editing the active entry, remove the end_time field.
        if self.instance.start_time and not self.instance.end_time:
            self.fields.pop('end_time')

    def clean(self):
        """
        If we're not editing the active entry, ensure that this entry doesn't
        conflict with or come after the active entry.
        """
        active = utils.get_active_entry(self.user)
        start_time = self.cleaned_data.get('start_time', None)
        end_time = self.cleaned_data.get('end_time', None)

        if active and active.pk != self.instance.pk:
            if (start_time and start_time > active.start_time) or \
                    (end_time and end_time > active.start_time):
                raise forms.ValidationError(
                    'The start time or end time conflict with the active '
                    'entry: {activity} on {project} starting at '
                    '{start_time}.'.format(
                        project=active.project,
                        activity=active.activity,
                        start_time=active.start_time.strftime('%H:%M:%S'),
                    ))

        month_start = utils.get_month_start(start_time)
        next_month = month_start + relativedelta(months=1)
        entries = self.instance.user.timepiece_entries.filter(
            Q(status=Entry.APPROVED) | Q(status=Entry.INVOICED),
            start_time__gte=month_start,
            end_time__lt=next_month
        )
        entry = self.instance

        if not self.acting_user.is_superuser:
            if (entries.exists() and not entry.id or entry.id and entry.status == Entry.INVOICED):
                message = 'You cannot add/edit entries after a timesheet has been ' \
                    'approved or invoiced. Please correct the start and end times.'
                raise forms.ValidationError(message)

        return self.cleaned_data


class ProjectHoursForm(forms.ModelForm):

    class Meta:
        model = ProjectHours
        fields = ['week_start', 'project', 'user', 'hours', 'published']

    def save(self, commit=True):
        ph = super(ProjectHoursForm, self).save()
        # since hours are being assigned to a user, add the user
        # to the project if they are not already in it so they can track time
        ProjectRelationship.objects.get_or_create(user=self.cleaned_data['user'],
                                                  project=self.cleaned_data['project'])
        return ph


class ProjectHoursSearchForm(forms.Form):
    week_start = forms.DateField(
        label='Week of', required=False,
        input_formats=INPUT_FORMATS, widget=TimepieceDateInput())

    def clean_week_start(self):
        week_start = self.cleaned_data.get('week_start', None)
        return utils.get_week_start(week_start, False) if week_start else None
