import datetime
from dateutil.relativedelta import relativedelta

from django import forms
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Q, Sum

from timepiece import utils
from timepiece.crm.models import Project, ProjectRelationship
from timepiece.entries.lookups import ActivityLookup
from timepiece.entries.models import Entry, Location, ProjectHours, Activity
from timepiece.forms import INPUT_FORMATS, TimepieceSplitDateTimeField,\
        TimepieceDateInput

from selectable import forms as selectable


class ClockInForm(forms.ModelForm):
    active_comment = forms.CharField(
        label='Notes for the active entry', widget=forms.Textarea,
        required=False)
    start_time = TimepieceSplitDateTimeField(required=False)

    class Meta:
        model = Entry
        fields = ('active_comment', 'location', 'project', 'activity',
                  'start_time', 'comments')
        # disabling this widget because it does not seem to work as nicely
        # as what I previously had working
        # widgets = {
        #     'activity': selectable.AutoComboboxSelectWidget(lookup_class=ActivityLookup),
        # }

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

        # TODO: Danny - WHY DID I ADD THESE TWO LINES?
        self.fields['start_time'].required = False
        self.fields['start_time'].read_only = True

        self.fields['start_time'].initial = datetime.datetime.now()
        self.fields['project'].queryset = Project.trackable.filter(
                users=self.user)
        
        # TODO: seems there must be a better way to do this
        if args[0] and args[0].get('project', 0):
            p = Project.objects.get(id=int(args[0].get('project', 0)))
            if p.activity_group:
                self.fields['activity'].queryset = Activity.objects.filter(
                    id__in=[v['id'] for v in p.activity_group.activities.values()])
            else:
                self.fields['activity'].queryset = Activity.objects.filter()
        
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

            # TODO: think of a better, cleaner integration
            try:
                if hasattr(self.active,'generaltask_set'):
                    from workflow.general_task import emails
                    gt = self.active.generaltask_set.all()[0]
                    if gt.hours_spent >= gt.effort:
                        emails.overspent(gt,
                            reverse('view_general_task', args=(gt.id,)),
                            reverse('edit_general_task', args=(gt.id,)))
            except:
                pass

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
    hours_paused = forms.FloatField(required=False, label='Hours Paused')

    class Meta:
        model = Entry
        exclude = ('user', 'pause_time', 'site', 'hours', 'status',
                   'entry_group', 'seconds_paused')
        fields = ('project', 'activity', 'location', 'start_time',
                  'end_time', 'hours_paused', 'comments')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.acting_user = kwargs.pop('acting_user')
        super(AddUpdateEntryForm, self).__init__(*args, **kwargs)
        self.instance.user = self.user
        self.fields['project'].queryset = Project.trackable.filter(
                users=self.user)
        
        self.fields['activity'].queryset = Activity.objects.filter()
        if self.instance:
            try:
                proj = self.instance.project
                if proj and proj.activity_group:
                    self.fields['activity'].queryset = Activity.objects.filter(
                        id__in=[v['id'] for v in proj.activity_group.activities.values()])
            except:
                pass
            
            # If editing the active entry, remove the end_time field.
            if self.instance.start_time and not self.instance.end_time:
                self.fields.pop('end_time')

            self.fields['hours_paused'].initial = self.instance.seconds_paused / 3600.

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
                raise forms.ValidationError('The start time or end time '
                        'conflict with the active entry: {activity} on '
                        '{project} starting at {start_time}.'.format(
                            project=active.project,
                            activity=active.activity,
                            start_time=active.start_time.strftime('%H:%M:%S'),
                        ))
        hours_paused = self.cleaned_data.get('hours_paused', 0)
        if type(hours_paused) != float and type(hours_paused) != int:
            self.cleaned_data['hours_paused'] = 0
            hours_paused = 0
        if hours_paused < 0:
            raise forms.ValidationError('The hours paused must be >= 0.')

        total_time = (self.cleaned_data.get('end_time', 
            datetime.datetime.now()) - self.cleaned_data.get(
            'start_time', datetime.datetime.now())
            ).seconds / 3600.0 + hours_paused
        if total_time  > 20.0:
            raise forms.ValidationError('The total time entry, '
                'including paused time, must be less than 20.0 hours.  '
                'Ensure that you entered the pause time in hours.')

        # month_start = utils.get_month_start(start_time)
        # next_month = month_start + relativedelta(months=1)
        # entries = self.instance.user.timepiece_entries.filter(
        #     Q(status=Entry.APPROVED) | Q(status=Entry.INVOICED),
        #     start_time__gte=month_start,
        #     end_time__lt=next_month
        # )
        period_start, period_end = utils.get_bimonthly_dates(start_time)
        entries = self.instance.user.timepiece_entries.filter(
            Q(status=Entry.APPROVED) | Q(status=Entry.INVOICED),
            start_time__gte=period_start,
            end_time__lt=period_end
        )

        entry = self.instance

        if not self.acting_user.is_superuser:
            if (entries.exists() and not entry.id or entry.id and entry.status == Entry.INVOICED):
                message = 'You cannot add/edit entries after a timesheet has been ' \
                    'approved or invoiced. Please correct the start and end times.'
                raise forms.ValidationError(message)

        return self.cleaned_data

    def save(self, commit=True):
        entry = super(AddUpdateEntryForm, self).save(commit=False)
        entry.seconds_paused = int(self.cleaned_data.get('hours_paused', 0) * 3600)
        if commit:
            entry.save()
        return entry


class WritedownEntryForm(forms.Form):
    hours = forms.FloatField(required=True)
    writedown = forms.BooleanField(required=True, initial=False, label='Writedown')
    comments = forms.CharField(label='Note for writedown entry.',
            widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        self.orig_entry = kwargs.pop('orig_entry')
        super(WritedownEntryForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(WritedownEntryForm, self).clean()
        if not self.orig_entry.project.billable:
            raise forms.ValidationError("You can only writedown time entries "
                "that were charged against a billable project.")
        if not self.orig_entry.activity.billable:
            raise forms.ValidationError("You can only writedown time entries "
                "that were charged against a billable activity.")

        hours = cleaned_data.get('hours', 0.0)
        # other_writedown_hours = Entry.objects.filter(writedown=True, 
        #     writedown_entry=self.orig_entry).aggregate(
        #     Sum('hours'))['hours__sum'] or 0.0
        # these hours would be negative, so subtract to add
        total_hours = float(hours)+float(self.orig_entry.written_down_hours)
        if total_hours > float(self.orig_entry.hours):
            raise forms.ValidationError("You cannot writedown more hours than"
                "the original time entry.  You may need to writedown multiple"
                "time entries.")
        return cleaned_data



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
    week_start = forms.DateField(label='Enter Date: ', required=False,
            input_formats=INPUT_FORMATS, widget=TimepieceDateInput())

    def clean_week_start(self):
        week_start = self.cleaned_data.get('week_start', None)
        return utils.get_period_start(week_start, False) if week_start else None
