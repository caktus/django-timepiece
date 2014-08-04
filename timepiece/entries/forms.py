import datetime
from dateutil.relativedelta import relativedelta

from django import forms

from timepiece import utils
from timepiece.crm.models import Project
from timepiece.entries.models import Entry, Location, ProjectHours
from timepiece.forms import INPUT_FORMATS, TimepieceSplitDateTimeWidget,\
        TimepieceDateInput


class ClockInForm(forms.ModelForm):
    active_comment = forms.CharField(label='Notes for the active entry',
            widget=forms.Textarea, required=False)

    class Meta:
        model = Entry
        fields = ('active_comment', 'location', 'project', 'activity',
                'start_time', 'comments')

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

        self.fields['start_time'].required = False
        self.fields['start_time'].read_only = True
        self.fields['start_time'].initial = datetime.datetime.now()
        self.fields['start_time'].widget = TimepieceSplitDateTimeWidget()
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
        # DISABLED FOR NOW SINCE WE DO NOT CARE ABOUT OVERLAPPING
        # active_entries = self.user.timepiece_entries.filter(
        #     start_time__gte=start, end_time__isnull=True)
        # for entry in active_entries:
        #     output = 'The start time is on or before the current entry: ' + \
        #     '%s - %s starting at %s' % (entry.project, entry.activity,
        #         entry.start_time.strftime('%H:%M:%S'))
        #     raise forms.ValidationError(output)
        if start > datetime.datetime.now():
            raise forms.ValidationError('The start time cannot be in the future.')
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
    start_time = forms.DateTimeField(widget=TimepieceSplitDateTimeWidget)
    end_time = forms.DateTimeField(widget=TimepieceSplitDateTimeWidget)

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
    start_time = forms.DateTimeField(widget=TimepieceSplitDateTimeWidget(),
            required=True)
    end_time = forms.DateTimeField(widget=TimepieceSplitDateTimeWidget())
    hours_paused = forms.FloatField(required=False, label='Hours Paused')

    class Meta:
        model = Entry
        exclude = ('user', 'pause_time', 'site', 'hours', 'status',
                   'entry_group', 'seconds_paused')
        fields = ('project', 'activity', 'location', 'start_time',
                  'end_time', 'hours_paused', 'comments')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
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
        if active and active.pk != self.instance.pk:
            start_time = self.cleaned_data.get('start_time', None)
            end_time = self.cleaned_data.get('end_time', None)
            if (start_time and start_time > active.start_time) or \
                    (end_time and end_time > active.start_time):
                raise forms.ValidationError('The start time or end time '
                        'conflict with the active entry: {activity} on '
                        '{project} starting at {start_time}.'.format(**{
                            'project': active.project,
                            'activity': active.activity,
                            'start_time': active.start_time.strftime('%H:%M:%S'),
                        }))
        hours_paused = self.cleaned_data.get('hours_paused', 0)
        if type(hours_paused) != float and type(hours_paused) != int:
            self.cleaned_data['hours_paused'] = 0
            hours_paused = 0
        if hours_paused < 0:
            raise forms.ValidationError('The hours paused must be >= 0.')
        return self.cleaned_data

    def save(self, commit=True):
        entry = super(AddUpdateEntryForm, self).save(commit=False)
        entry.seconds_paused = int(self.cleaned_data.get('hours_paused', 0) * 3600)
        if commit:
            entry.save()
        return entry


class ProjectHoursForm(forms.ModelForm):

    class Meta:
        model = ProjectHours


class ProjectHoursSearchForm(forms.Form):
    week_start = forms.DateField(label='Enter Date: ', required=False,
            input_formats=INPUT_FORMATS, widget=TimepieceDateInput())

    def clean_week_start(self):
        week_start = self.cleaned_data.get('week_start', None)
        return utils.get_period_start(week_start, False) if week_start else None
