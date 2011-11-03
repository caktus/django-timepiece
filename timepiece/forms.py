from decimal import Decimal
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
from lookups import ProjectLookup

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
   
    billable = forms.BooleanField(initial=True, required=False)
    non_billable = forms.BooleanField(label='Non-Billable', initial=True,
                                      required=False)
    trunc = forms.ChoiceField(choices=TRUNC_CHOICES,
                              widget=forms.RadioSelect(), initial='month')
    pj_select = selectable_forms.AutoCompleteSelectField(ProjectLookup,
        label='Project Name:',
        required=False,
    )
    pjs = forms.ModelMultipleChoiceField(queryset=Project.objects.all(),
                                         required=False)
    pj_list = []

    def clean(self, *args, **kwargs):
        super(ProjectFiltersForm, self).clean(*args, **kwargs)
        pj_add = self.cleaned_data.get('pj_select', None)
        pjs = self.cleaned_data.get('pjs', None)
        if pj_add:
            if pj_add.pk not in self.pj_list:
                self.pj_list.append(pj_add.pk)
        if pjs:
            rms = [pj.pk for pj in pjs]
            print "pj_list:", self.pj_list
            print "Pjs:", pjs

            print "rms", rms
            try:
                self.pj_list.remove(rms)
            except ValueError:
                return self.cleaned_data
            query = Project.objects.filter(id__in=self.pj_list)
            self.fields['pjs'].queryset = query
        return self.cleaned_data



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
        exclude = ('user', 'pause_time', 'site', 'hours', 'status',)

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
        if start >= datetime.now() or end and end > datetime.now():
            raise forms.ValidationError(
                'Entries may not be added in the future.')
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

    def save(self):
        from_date = self.cleaned_data.get('from_date', '')
        to_date = self.cleaned_data.get('to_date', '')
        if to_date:
            to_date += timedelta(days=1)
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
