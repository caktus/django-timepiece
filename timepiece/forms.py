from decimal import Decimal
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from django import forms
from django.db.models import Q
from django.conf import settings
from django.contrib.auth import models as auth_models
from django.contrib.auth import forms as auth_forms
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS

from selectable import forms as selectable_forms
from timepiece.lookups import ProjectLookup

from ajax_select.fields import AutoCompleteSelectMultipleField, \
                               AutoCompleteSelectField, \
                               AutoCompleteSelectWidget

from timepiece.models import Project, Entry, Activity, UserProfile
from timepiece.fields import PendulumDateTimeField
from timepiece.widgets import PendulumDateTimeWidget, SecondsToHoursWidget
from timepiece import models as timepiece
from timepiece import utils


class ProjectFiltersForm(forms.Form):
    TRUNC_CHOICES = [
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
    ]
    DEFAULT_TRUNC = TRUNC_CHOICES[2][0]
    billable = forms.BooleanField(initial=True, required=False)
    non_billable = forms.BooleanField(label='Non-Billable', initial=True,
                                      required=False)
    paid_leave = forms.BooleanField(initial=True, required=False)
    trunc = forms.ChoiceField(label='Group Totals By:', choices=TRUNC_CHOICES,
                              widget=forms.RadioSelect(), required=False,
                              initial=DEFAULT_TRUNC)
    pj_select = selectable_forms.AutoCompleteSelectMultipleField(ProjectLookup,
        label='Project Name:', required=False)

    def clean_trunc(self):
        trunc = self.cleaned_data.get('trunc', '')
        if not trunc:
            trunc = self.DEFAULT_TRUNC
        return trunc

    def get_hour_type(self):
        try:
            billable = self.cleaned_data.get('billable', False)
            non_billable = self.cleaned_data.get('non_billable', False)
        except AttributeError:
            return 'total'
        if billable and non_billable:
            return 'total'
        elif billable:
            return 'billable'
        elif non_billable:
            return 'non_billable'
        return 'nothing'


class CreatePersonForm(auth_forms.UserCreationForm):
    class Meta:
        model = auth_models.User
        fields = (
            "username", "first_name", "last_name",
            "email", "is_active", "is_staff")


class EditPersonForm(auth_forms.UserChangeForm):
    password_one = forms.CharField(required=False, max_length=36,
        label=_(u'Password'), widget=forms.PasswordInput(render_value=False))
    password_two = forms.CharField(required=False, max_length=36,
        label=_(u'Repeat Password'),
        widget=forms.PasswordInput(render_value=False))

    class Meta:
        model = auth_models.User
        fields = (
            "username", "first_name", "last_name",
            "email", "is_active", "is_staff"
        )

    def clean(self):
        super(EditPersonForm, self).clean()
        password_one = self.cleaned_data.get('password_one', None)
        password_two = self.cleaned_data.get('password_two', None)
        if password_one and password_one != password_two:
            raise forms.ValidationError(_('Passwords Must Match.'))
        return self.cleaned_data

    def save(self, *args, **kwargs):
        commit = kwargs.get('commit', True)
        kwargs['commit'] = False
        instance = super(EditPersonForm, self).save(*args, **kwargs)
        password_one = self.cleaned_data.get('password_one', None)
        if password_one:
            instance.set_password(password_one)
        if commit:
            instance.save()
        return instance


class CharAutoCompleteSelectWidget(AutoCompleteSelectWidget):
    def value_from_datadict(self, data, files, name):
        return data.get(name, None)


class QuickSearchForm(forms.Form):
    quick_search = AutoCompleteSelectField(
        'quick_search',
        widget=CharAutoCompleteSelectWidget('quick_search'),
    )

    def clean_quick_search(self):
        item = self.cleaned_data['quick_search']
        if isinstance(item, timepiece.Project):
            return reverse('view_project', kwargs={
                'project_id': item.id,
            })
        elif isinstance(item, timepiece.Business,):
            return reverse('view_business', kwargs={
                'business': item.id,
            })
        elif isinstance(item, auth_models.User,):
            return reverse('view_person', kwargs={
                'person_id': item.id,
            })
        raise forms.ValidationError('Must be a User or Project')

    def save(self):
        return self.cleaned_data['quick_search']


class SearchForm(forms.Form):
    search = forms.CharField(required=False)


class AddUserToProjectForm(forms.Form):
    user = AutoCompleteSelectField('user')

    def save(self):
        return self.cleaned_data['user']


class ClockInForm(forms.ModelForm):
    class Meta:
        model = timepiece.Entry
        fields = ('location', 'project', 'activity', 'start_time',)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        initial = kwargs.get('initial', {})
        default_loc = getattr(
            settings,
            'TIMEPIECE_DEFAULT_LOCATION_SLUG',
            None,
        )
        if default_loc:
            try:
                loc = timepiece.Location.objects.get(slug=default_loc)
            except timepiece.Location.DoesNotExist:
                loc = None
            if loc:
                initial['location'] = loc.pk
        project = initial.get('project')
        try:
            last_project_entry = timepiece.Entry.objects.filter(
                user=self.user, project=project).order_by('-end_time')[0]
        except IndexError:
            initial['activity'] = None
        else:
            initial['activity'] = last_project_entry.activity.id
        super(ClockInForm, self).__init__(*args, **kwargs)
        self.fields['start_time'].required = False
        self.fields['start_time'].initial = datetime.now()
        self.fields['start_time'].widget = forms.SplitDateTimeWidget(
            attrs={'class': 'timepiece-time'},
            date_format='%m/%d/%Y',
        )
        self.fields['project'].queryset = timepiece.Project.objects.filter(
            users=self.user, status__enable_timetracking=True,
            type__enable_timetracking=True
        )
        self.instance.user = self.user

    def clean_start_time(self):
        """
        Make sure that the start time doesn't come before the active entry
        """
        start = self.cleaned_data['start_time']
        active_entries = self.user.timepiece_entries.filter(
            start_time__gte=start, end_time__isnull=True)
        for entry in active_entries:
            output = 'The start time is on or before the current entry: ' + \
            '%s - %s starting at %s' % (entry.project, entry.activity,
                entry.start_time.strftime('%H:%M:%S'))
            raise forms.ValidationError(output)
        return start

    def save(self, commit=True):
        entry = super(ClockInForm, self).save(commit=False)
        entry.hours = 0
        entry.clock_in(self.user, self.cleaned_data['project'])
        if commit:
            entry.save()
        return entry


class ClockOutForm(forms.ModelForm):
    class Meta:
        model = timepiece.Entry
        fields = ('location', 'comments', 'start_time', 'end_time')

    def __init__(self, *args, **kwargs):
        kwargs['initial'] = {'end_time': datetime.now()}
        super(ClockOutForm, self).__init__(*args, **kwargs)
        self.fields['start_time'] = forms.DateTimeField(
            widget=forms.SplitDateTimeWidget(
                attrs={'class': 'timepiece-time'},
                date_format='%m/%d/%Y',
            )

        )
        self.fields['end_time'] = forms.DateTimeField(
            widget=forms.SplitDateTimeWidget(
                attrs={'class': 'timepiece-time'},
                date_format='%m/%d/%Y',
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
            date_format='%m/%d/%Y',
        )
    )
    end_time = forms.DateTimeField(
        widget=forms.SplitDateTimeWidget(
            attrs={'class': 'timepiece-time'},
            date_format='%m/%d/%Y',
        )
    )

    class Meta:
        model = Entry
        exclude = ('user', 'pause_time', 'site', 'hours', 'status',
                   'entry_group')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(AddUpdateEntryForm, self).__init__(*args, **kwargs)
        self.fields['project'].queryset = timepiece.Project.objects.filter(
            users=self.user,
        )
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


STATUS_CHOICES = [('', '---------'), ]
STATUS_CHOICES.extend(timepiece.ENTRY_STATUS)


class DateForm(forms.Form):
    from_date = forms.DateField(label="From", required=False)
    to_date = forms.DateField(label="To", required=False)
    status = forms.ChoiceField(choices=STATUS_CHOICES,
        widget=forms.HiddenInput(), required=False)
    activity = forms.ModelChoiceField(
        queryset=timepiece.Activity.objects.all(),
        widget=forms.HiddenInput(), required=False,
    )
    project = forms.ModelChoiceField(
        queryset=timepiece.Project.objects.all(),
        widget=forms.HiddenInput(), required=False,
    )

    def clean(self):
        data = self.cleaned_data
        from_date = data.get('from_date', None)
        to_date = data.get('to_date', None)
        if from_date and to_date and from_date > to_date:
            err_msg = 'The ending date must exceed the beginning date'
            raise ValidationError(err_msg)
        return data

    def save(self):
        from_date = self.cleaned_data.get('from_date', '')
        to_date = self.cleaned_data.get('to_date', '')
        if to_date:
            to_date += timedelta(days=1)
        return (from_date, to_date)


class YearMonthForm(forms.Form):
    MONTH_CHOICES = [(i, time.strftime('%B', time.strptime(str(i), '%m'))) \
                     for i in xrange(1, 13)]
    year = forms.ChoiceField()
    month = forms.ChoiceField(choices=MONTH_CHOICES)

    def __init__(self, *args, **kwargs):
        super(YearMonthForm, self).__init__(*args, **kwargs)
        now = datetime.now()
        this_year = now.year
        this_month = now.month
        try:
            first_entry = timepiece.Entry.objects.all().order_by('end_time')[0]
        except IndexError:
            first_year = this_year
        else:
            first_year = first_entry.end_time.year
        years = [(year, year) for year in xrange(first_year, this_year + 1)]
        self.fields['year'].choices = years
        initial = kwargs.get('initial')
        if initial:
            this_year = initial.get('year', this_year)
            this_month = initial.get('month', this_month)
        self.fields['year'].initial = this_year
        self.fields['month'].initial = this_month

    def save(self):
        now = datetime.now()
        this_year = now.year
        this_month = now.month
        month = int(self.cleaned_data.get('month', this_month))
        year = int(self.cleaned_data.get('year', this_year))
        from_date = datetime(year, month, 1)
        to_date = from_date + relativedelta(months=1)
        return (from_date, to_date)


class ProjectionForm(DateForm):
    user = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        users = kwargs.pop('users')
        super(ProjectionForm, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = users


class BusinessForm(forms.ModelForm):
    class Meta:
        model = timepiece.Business
        fields = ('name', 'email', 'description', 'notes',)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = timepiece.Project
        fields = (
            'name',
            'business',
            'trac_environment',
            'point_person',
            'type',
            'status',
            'activity_group',
            'description',
        )

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)

    def save(self):
        instance = super(ProjectForm, self).save(commit=False)
        instance.save()
        return instance


class ProjectRelationshipForm(forms.ModelForm):
    class Meta:
        model = timepiece.ProjectRelationship
        fields = ('types',)

    def __init__(self, *args, **kwargs):
        super(ProjectRelationshipForm, self).__init__(*args, **kwargs)
        self.fields['types'].widget = forms.CheckboxSelectMultiple(
            choices=self.fields['types'].choices
        )
        self.fields['types'].help_text = ''


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = timepiece.EntryGroup
        fields = ('status', 'number', 'comments')

    def save(self, commit=True):
        instance = super(InvoiceForm, self).save(commit=False)
        instance.project = self.initial['project']
        instance.user = self.initial['user']
        from_date = self.initial['from_date']
        to_date = self.initial['to_date']
        instance.start = from_date
        instance.end = to_date
        instance.save()
        return instance


class RepeatPeriodForm(forms.ModelForm):
    class Meta:
        model = timepiece.RepeatPeriod
        fields = ('active', 'count', 'interval')

    def __init__(self, *args, **kwargs):
        super(RepeatPeriodForm, self).__init__(*args, **kwargs)
        self.fields['count'].required = False
        self.fields['interval'].required = False
        self.fields['date'] = forms.DateField(required=False)

    def _clean_optional(self, name):
        active = self.cleaned_data.get('active', False)
        value = self.cleaned_data.get(name, '')
        if active and not value:
            raise forms.ValidationError('This field is required.')
        return self.cleaned_data[name]

    def clean_count(self):
        return self._clean_optional('count')

    def clean_interval(self):
        return self._clean_optional('interval')

    def clean_date(self):
        active = self.cleaned_data.get('active', False)
        date = self.cleaned_data.get('date', '')
        if active and not self.instance.id and not date:
            raise forms.ValidationError(
                'Start date is required for new billing periods')
        return date

    def clean(self):
        date = self.cleaned_data.get('date', '')
        if self.instance.id and date:
            latest = self.instance.billing_windows.latest()
            if self.cleaned_data['active'] and date < latest.end_date:
                raise forms.ValidationError(
                    'New start date must be after %s' % latest.end_date)
        return self.cleaned_data

    def save(self):
        period = super(RepeatPeriodForm, self).save(commit=False)
        if not self.instance.id and period.active:
            period.save()
            period.billing_windows.create(
                date=self.cleaned_data['date'],
                end_date=self.cleaned_data['date'] + period.delta(),
            )
        elif self.instance.id:
            period.save()
            start_date = self.cleaned_data['date']
            if period.active and start_date:
                latest = period.billing_windows.latest()
                if start_date > latest.end_date:
                    period.billing_windows.create(
                        date=latest.end_date,
                        end_date=start_date + period.delta(),
                    )
        period.update_billing_windows()
        return period


class PersonTimeSheet(forms.ModelForm):
    class Meta:
        model = timepiece.PersonRepeatPeriod
        fields = ('user',)

    def __init__(self, *args, **kwargs):
        super(PersonTimeSheet, self).__init__(*args, **kwargs)
        self.fields['user'].queryset = \
            auth_models.User.objects.all().order_by('last_name')


class SearchForm(forms.Form):
    search = forms.CharField(required=False)


class UserForm(forms.ModelForm):

    class Meta:
        model = auth_models.User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        for name in self.fields:
            self.fields[name].required = True


class UserProfileForm(forms.ModelForm):

    class Meta:
        model = timepiece.UserProfile
        exclude = ('user',)
