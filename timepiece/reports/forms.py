from django import forms
from django.contrib.auth.models import User

from selectable import forms as selectable

from timepiece.fields import UserModelMultipleChoiceField
from timepiece.forms import DateForm, YearMonthForm

from timepiece.crm.lookups import ProjectLookup, ProjectCodeLookup, \
    BusinessLookup, UserLookup, ActivityLookup
from timepiece.contracts.lookups import ContractLookup
from timepiece.crm.models import Attribute
from timepiece.entries.models import Entry, Activity


class BillableHoursReportForm(DateForm):
    TRUNC_CHOICES = (
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
    )

    trunc = forms.ChoiceField(label='Group Totals By', choices=TRUNC_CHOICES,
            widget=forms.RadioSelect())
    users = UserModelMultipleChoiceField(required=False, queryset=None,
            widget=forms.CheckboxSelectMultiple())
    activities = forms.ModelMultipleChoiceField(required=False, queryset=None,
            widget=forms.CheckboxSelectMultiple())
    project_types = forms.ModelMultipleChoiceField(required=False,
            queryset=None, widget=forms.CheckboxSelectMultiple())

    def __init__(self, *args, **kwargs):
        """
        If the 'select_all' argument is given, any data values for users,
        activities, and project_types are overwritten with all available
        choices.
        """
        select_all = kwargs.pop('select_all', False)

        super(BillableHoursReportForm, self).__init__(*args, **kwargs)
        self.fields['from_date'].required = True
        self.fields['to_date'].required = True

        user_ids = Entry.no_join.values_list('user', flat=True)
        users = User.objects.filter(id__in=user_ids)
        activities = Activity.objects.all()
        project_types = Attribute.objects.all()

        self.fields['users'].queryset = users
        self.fields['activities'].queryset = activities
        self.fields['project_types'].queryset = project_types

        if select_all:
            self.data['users'] = list(users.values_list('id', flat=True))
            self.data['activities'] = list(activities.values_list('id',
                    flat=True))
            self.data['project_types'] = list(project_types.values_list('id',
                    flat=True))


class ProductivityReportForm(forms.Form):
    ORGANIZE_BY_CHOICES = (
        ('project', 'Project'),
        ('activity', 'Activity'),
        ('user', 'User'),
        # ('week', 'Week'),
    )
    
    business = selectable.AutoCompleteSelectField(BusinessLookup,
        label='Client', required=False)
    project_statuses = forms.ModelMultipleChoiceField(required=False,
        label='Project Status',
        help_text='If you do not provide a Project, select one or more Project Statuses.',
        queryset=Attribute.objects.filter(type='project-status'),
        widget=forms.CheckboxSelectMultiple)

    project = selectable.AutoCompleteSelectField(ProjectCodeLookup,
        label='Project', required=False)

    billable = forms.BooleanField(required=False)
    non_billable = forms.BooleanField(label='Non-billable', required=False)
    writedown = forms.BooleanField(label='Include Writedowns', required=False)
    # paid_time_off = forms.BooleanField(required=False)
    # unpaid_time_off = forms.BooleanField(required=False)

    organize_by = forms.ChoiceField(choices=ORGANIZE_BY_CHOICES,
        widget=forms.RadioSelect(), initial=ORGANIZE_BY_CHOICES[0][0])


class HourlyReportForm(DateForm):
    TRUNC_CHOICES = (
        ('day', 'Day'),
        ('week', 'Week'),
        ('month', 'Month'),
        ('year', 'Year'),
    )

    billable = forms.BooleanField(required=False)
    non_billable = forms.BooleanField(label='Non-billable', required=False)
    writedown = forms.BooleanField(label='Include Writedowns', required=False)
    paid_time_off = forms.BooleanField(required=False)
    unpaid_time_off = forms.BooleanField(required=False)
    trunc = forms.ChoiceField(label='Group Totals By', choices=TRUNC_CHOICES,
            widget=forms.RadioSelect())
    projects = selectable.AutoCompleteSelectMultipleField(ProjectLookup,
            label='Project Name', required=False)
    businesses = selectable.AutoCompleteSelectMultipleField(BusinessLookup,
            label='Client Name', required=False)

    def __init__(self, *args, **kwargs):
        super(HourlyReportForm, self).__init__(*args, **kwargs)
        self.fields['from_date'].required = True
        self.fields['to_date'].required = True

class RevenueReportForm(DateForm):

    projects = selectable.AutoCompleteSelectMultipleField(ProjectLookup,
            label='Project', required=False)
    contracts = selectable.AutoCompleteSelectMultipleField(ContractLookup,
            label='Contract', required=False)
    employees = selectable.AutoCompleteSelectMultipleField(UserLookup,
            label='Employee', required=False)

    def __init__(self, *args, **kwargs):
        super(RevenueReportForm, self).__init__(*args, **kwargs)
        self.fields['from_date'].required = True
        self.fields['to_date'].required = True

class PayrollSummaryReportForm(YearMonthForm):
    pass

class BacklogFilterForm(forms.Form):
    project_statuses = forms.ModelMultipleChoiceField(required=False,
        label='Project Status',
        queryset=Attribute.objects.filter(type='project-status'),
        widget=forms.CheckboxSelectMultiple)
    project_types = forms.ModelMultipleChoiceField(required=False,
        label='Project Type',
        queryset=Attribute.objects.filter(type='project-type'),
        widget=forms.CheckboxSelectMultiple)

    projects = selectable.AutoCompleteSelectMultipleField(ProjectCodeLookup,
        label="Project(s)", required=False)
    activities = selectable.AutoCompleteSelectMultipleField(ActivityLookup,
        label="Activitie(s)", required=False)
    clients = selectable.AutoCompleteSelectMultipleField(BusinessLookup,
        label="Client(s)", required=False)

    billable = forms.BooleanField(required=False)
    non_billable = forms.BooleanField(label='Non-billable', required=False)
