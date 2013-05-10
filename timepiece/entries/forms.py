import datetime
from dateutil.relativedelta import relativedelta

from django import forms
from django.db.models import Q

from timepiece import utils
from timepiece.forms import DATE_FORM_FORMAT

from timepiece.crm.models import Project
from timepiece.entries.models import Entry, Activity, Location, ProjectHours


class ClockInForm(forms.ModelForm):
    active_comment = forms.CharField(label='Notes for the active entry',
                                     widget=forms.Textarea, required=False)

    class Meta:
        model = Entry
        fields = (
            'active_comment', 'location', 'project', 'activity', 'start_time',
            'comments'
        )

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
        project = initial.get('project')
        try:
            last_project_entry = Entry.objects.filter(
                user=self.user, project=project).order_by('-end_time')[0]
        except IndexError:
            initial['activity'] = None
        else:
            initial['activity'] = last_project_entry.activity.id
        super(ClockInForm, self).__init__(*args, **kwargs)
        self.fields['start_time'].required = False
        self.fields['start_time'].initial = datetime.datetime.now()
        self.fields['start_time'].widget = forms.SplitDateTimeWidget(
            attrs={'class': 'timepiece-time'},
            date_format=DATE_FORM_FORMAT
        )
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
            output = 'The start time is on or before the current entry: ' + \
            '%s - %s starting at %s' % (entry.project, entry.activity,
                entry.start_time.strftime('%H:%M:%S'))
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
        entry = super(ClockInForm, self).save(commit=False)
        entry.hours = 0
        entry.clock_in(self.user, self.cleaned_data['project'])
        if commit:
            entry.save()
            if self.active:
                self.active.save()
        return entry


class ClockOutForm(forms.ModelForm):

    class Meta:
        model = Entry
        fields = ('location', 'comments', 'start_time', 'end_time')

    def __init__(self, *args, **kwargs):
        kwargs['initial'] = {'end_time': datetime.datetime.now()}
        super(ClockOutForm, self).__init__(*args, **kwargs)
        self.fields['start_time'] = forms.DateTimeField(
            widget=forms.SplitDateTimeWidget(
                attrs={'class': 'timepiece-time'},
                date_format=DATE_FORM_FORMAT,
            )

        )
        self.fields['end_time'] = forms.DateTimeField(
            widget=forms.SplitDateTimeWidget(
                attrs={'class': 'timepiece-time'},
                date_format=DATE_FORM_FORMAT,
            ),
        )

        self.fields.keyOrder = ('location', 'start_time',
            'end_time', 'comments')

    def save(self, commit=True):
        entry = super(ClockOutForm, self).save(commit=False)
        entry.end_time = self.cleaned_data['end_time']
        entry.unpause(date=self.cleaned_data['end_time'])
        if commit:
            entry.save()
        return entry


class AddUpdateEntryForm(forms.ModelForm):
    """
    This form will provide a way for users to add missed log entries and to
    update existing log entries.
    """
    start_time = forms.DateTimeField(
        widget=forms.SplitDateTimeWidget(
            attrs={'class': 'timepiece-time'},
            date_format=DATE_FORM_FORMAT,
        )
    )
    end_time = forms.DateTimeField(
        widget=forms.SplitDateTimeWidget(
            attrs={'class': 'timepiece-time'},
            date_format=DATE_FORM_FORMAT,
        )
    )

    class Meta:
        model = Entry
        exclude = ('user', 'pause_time', 'site', 'hours', 'status',
                   'entry_group')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(AddUpdateEntryForm, self).__init__(*args, **kwargs)
        self.fields['project'].queryset = Project.trackable.filter(
                users=self.user)
        #if editing a current entry, remove the end time field
        if self.instance.start_time and not self.instance.end_time:
            self.fields.pop('end_time')
        self.instance.user = self.user

    def clean(self):
        """
        Verify that the entry doesn't conflict with or come after the current
        entry, and that the times are valid for model clean
        """
        cleaned_data = self.cleaned_data
        start = cleaned_data.get('start_time', None)
        end = cleaned_data.get('end_time', None)
        if not start:
            raise forms.ValidationError(
                'Please enter a valid date/time.')
        #Obtain all current entries, except the one being edited
        times = [start, end] if end else [start]
        query = reduce(lambda q, time: q | Q(start_time__lte=time), times, Q())
        entries = self.user.timepiece_entries.filter(
            query, end_time__isnull=True
            ).exclude(id=self.instance.id)
        for entry in entries:
            output = 'The times below conflict with the current entry: ' + \
            '%s - %s starting at %s' % \
            (entry.project, entry.activity,
                entry.start_time.strftime('%H:%M:%S'))
            raise forms.ValidationError(output)
        return self.cleaned_data

    def save(self, commit=True):
        entry = super(AddUpdateEntryForm, self).save(commit=False)
        entry.user = self.user
        if commit:
            entry.save()
        return entry


class ProjectHoursSearchForm(forms.Form):
    week_start = forms.DateField(label='Week of', required=False,
            input_formats=(DATE_FORM_FORMAT,),
            widget=forms.DateInput(format=DATE_FORM_FORMAT))

    def clean_week_start(self):
        week_start = self.cleaned_data.get('week_start', None)
        return utils.get_week_start(week_start, False) if week_start else None


class ProjectHoursForm(forms.ModelForm):

    class Meta:
        model = ProjectHours
