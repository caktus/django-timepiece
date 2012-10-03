from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

from django import forms
from django.conf import settings
from django.contrib.auth import models as auth_models
from django.contrib.auth import forms as auth_forms
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from selectable import forms as selectable_forms

from timepiece import models as timepiece
from timepiece import utils
from timepiece.fields import UserModelChoiceField
from timepiece.lookups import ProjectLookup, QuickLookup
from timepiece.lookups import UserLookup, BusinessLookup
from timepiece.models import Project, Entry, Activity, UserProfile, Attribute
from timepiece.models import ProjectHours


class ProjectFiltersForm(forms.Form):
    TRUNC_CHOICES = [
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
    ]
    DEFAULT_TRUNC = TRUNC_CHOICES[1][0]
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
            "email", "is_active", "is_staff", "groups"
        )


class EditPersonForm(auth_forms.UserChangeForm):
    password_one = forms.CharField(required=False, max_length=36,
        label=_(u'Password'), widget=forms.PasswordInput(render_value=False))
    password_two = forms.CharField(required=False, max_length=36,
        label=_(u'Repeat Password'),
        widget=forms.PasswordInput(render_value=False))

    def __init__(self, *args, **kwargs):
        super(EditPersonForm, self).__init__(*args, **kwargs)

        # In 1.4 this field is created even if it is excluded in Meta.
        if 'password' in self.fields:
            del(self.fields['password'])

    def clean_password(self):
        return self.cleaned_data.get('password_one', None)

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

    class Meta:
        model = auth_models.User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active',
                'is_staff')


class QuickSearchForm(forms.Form):
    quick_search = selectable_forms.AutoCompleteSelectField(
        QuickLookup,
        label='Quick Search',
        required=False
    )
    quick_search.widget.attrs['placeholder'] = 'Search'

    def clean_quick_search(self):
        item = self.cleaned_data['quick_search']

        if item is not None:
            try:
                item = item.split('-')
                if len(item) == 1 or '' in item:
                    raise ValueError
                return item
            except ValueError:
                raise forms.ValidationError('%s' %
                    'User, business, or project does not exist')
        else:
            raise forms.ValidationError('%s' %
                'User, business, or project does not exist')

    def save(self):
        type, pk = self.cleaned_data['quick_search']

        if type == 'individual':
            return reverse('view_person', kwargs={
                'person_id': pk
            })
        elif type == 'business':
            return reverse('view_business', kwargs={
                'business': pk
            })
        elif type == 'project':
            return reverse('view_project', kwargs={
                'project_id': pk
            })

        raise forms.ValidationError('Must be a user, project, or business')


class AddUserToProjectForm(forms.Form):
    user = selectable_forms.AutoCompleteSelectField(UserLookup, label="")
    user.widget.attrs['placeholder'] = 'Add User'

    def save(self):
        return self.cleaned_data['user']


class ClockInForm(forms.ModelForm):
    active_comment = forms.CharField(label='Notes for the active entry',
                                     widget=forms.Textarea, required=False)

    class Meta:
        model = timepiece.Entry
        fields = (
            'active_comment', 'location', 'project', 'activity', 'start_time',
            'comments'
        )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.active = kwargs.pop('active', None)
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
            self.active.end_time = start_time - timedelta(seconds=1)
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
            users=self.user, status__enable_timetracking=True,
            type__enable_timetracking=True
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
    DATE_FORMAT = '%m/%d/%Y'

    from_date = forms.DateField(label="From", required=False,
        input_formats=(DATE_FORMAT,),
        widget=forms.DateInput(format=DATE_FORMAT))
    to_date = forms.DateField(label="To", required=False,
        input_formats=(DATE_FORMAT,),
        widget=forms.DateInput(format=DATE_FORMAT))

    def clean(self):
        data = self.cleaned_data
        from_date = data.get('from_date', None)
        to_date = data.get('to_date', None)
        if from_date and to_date and from_date > to_date:
            err_msg = 'The ending date must exceed the beginning date'
            raise forms.ValidationError(err_msg)
        return data

    def save(self):
        from_date = self.cleaned_data.get('from_date', '')
        to_date = self.cleaned_data.get('to_date', '')
        returned_date = to_date

        if returned_date:
            returned_date += timedelta(days=1)
        return (from_date, returned_date)


class YearMonthForm(forms.Form):
    MONTH_CHOICES = [(i, time.strftime('%B', time.strptime(str(i), '%m'))) \
                     for i in xrange(1, 13)]
    month = forms.ChoiceField(choices=MONTH_CHOICES, label='')
    year = forms.ChoiceField(label='')

    def __init__(self, *args, **kwargs):
        super(YearMonthForm, self).__init__(*args, **kwargs)
        now = datetime.now()
        this_year = now.year
        this_month = now.month
        try:
            first_entry = timepiece.Entry.no_join.values('end_time')\
                                                 .order_by('end_time')[0]
        except IndexError:
            first_year = this_year
        else:
            first_year = first_entry['end_time'].year
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


class UserYearMonthForm(YearMonthForm):
    users = auth_models.User.objects.exclude(timepiece_entries=None) \
        .order_by('first_name')
    user = UserModelChoiceField(label='', queryset=users, required=False)

    def save(self):
        from_date, to_date = super(UserYearMonthForm, self).save()
        return  (from_date, to_date, self.cleaned_data.get('user', None))


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
            'tracker_url',
            'point_person',
            'type',
            'status',
            'activity_group',
            'description',
        )

    business = selectable_forms.AutoCompleteSelectField(
        BusinessLookup,
        label='Business',
        required=True
    )
    business.widget.attrs['placeholder'] = 'Search'

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


class SearchForm(forms.Form):
    search = forms.CharField(required=False, label='')
    search.widget.attrs['placeholder'] = 'Search'

    def save(self):
        search = self.cleaned_data.get('search', '')
        return search


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
        exclude = ('user', 'hours_per_week')


class ProjectSearchForm(SearchForm):
    status = forms.ChoiceField(required=False, choices=[], label='')

    def __init__(self, *args, **kwargs):
        super(ProjectSearchForm, self).__init__(*args, **kwargs)
        PROJ_STATUS_CHOICES = [('', 'Any Status')]
        PROJ_STATUS_CHOICES.extend([(a.pk, a.label) for a
                in Attribute.objects.all().filter(type="project-status")])
        self.fields['status'].choices = PROJ_STATUS_CHOICES

    def save(self):
        search = self.cleaned_data.get('search', '')
        status = self.cleaned_data.get('status', '')
        return (search, status)


class DeleteForm(forms.Form):
    """
    Returns True if the object was deleted
    """
    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super(DeleteForm, self).__init__(*args, **kwargs)

    def save(self):
        if self.instance:
            try:
                self.instance.delete()
            except AssertionError:
                return False
            else:
                return True
        return False


class BillableHoursForm(forms.Form):
    TRUNC_CHOICES = (
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
    )
    trunc = forms.ChoiceField(
        label='Group By',
        choices=TRUNC_CHOICES,
        widget=forms.RadioSelect(),
        required=False,
        initial=TRUNC_CHOICES[1][0])
    people = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    activities = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        queryset=timepiece.Activity.objects.all(),
        required=False,
        initial=timepiece.Activity.objects.all()
    )
    project_types = forms.ModelMultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(),
        queryset=timepiece.Attribute.objects.all(),
        required=False,
        initial=timepiece.Attribute.objects.all()
    )

    def __init__(self, *args, **kwargs):
        super(BillableHoursForm, self).__init__(*args, **kwargs)

        people = []
        users = timepiece.Entry.no_join.values('user', 'user__first_name',
            'user__last_name').distinct().order_by('user__first_name',
            'user__last_name')
        for u in users:
            name = ' '.join([u['user__first_name'], u['user__last_name']])
            person = (u['user'], name,)
            people.append(person)

        self.fields['people'].choices = people
        self.fields['people'].initial = [p[0] for p in people]

    def save(self):
        return {
            'people': self.cleaned_data['people'],
            'activities': self.cleaned_data['activities'],
            'project_types': self.cleaned_data['project_types']
        }


class ProjectHoursSearchForm(forms.Form):
    week_start = forms.DateField(label='Week of', required=False,
            input_formats=('%Y-%m-%d',),
            widget=forms.DateInput(format='%Y-%m-%d'))

    def clean_week_start(self):
        week_start = self.cleaned_data.get('week_start', None)
        return utils.get_week_start(week_start, False) if week_start else None


class ProjectHoursForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProjectHoursForm, self).__init__(*args, **kwargs)

    class Meta:
        model = ProjectHours
