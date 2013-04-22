from django import forms
from django.contrib.auth.models import User

from selectable import forms as selectable

from timepiece.fields import UserModelMultipleChoiceField
from timepiece.forms import DateForm, DATE_FORM_FORMAT, YearMonthForm
from timepiece.lookups import ProjectLookup
from timepiece.models import Entry, Activity

from timepiece.crm.models import Attribute


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
    DATE_FORMAT = DATE_FORM_FORMAT
    ORGANIZE_BY_CHOICES = (
        ('week', 'Week'),
        ('user', 'User'),
    )
    project = selectable.AutoCompleteSelectField(ProjectLookup)
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
    paid_leave = forms.BooleanField(required=False)
    trunc = forms.ChoiceField(label='Group Totals By', choices=TRUNC_CHOICES,
            widget=forms.RadioSelect())
    projects = selectable.AutoCompleteSelectMultipleField(ProjectLookup,
            label='Project Name', required=False)

    def __init__(self, *args, **kwargs):
        super(HourlyReportForm, self).__init__(*args, **kwargs)
        self.fields['from_date'].required = True
        self.fields['to_date'].required = True


class PayrollSummaryReportForm(YearMonthForm):
    pass
