from dateutil.relativedelta import relativedelta

from django import forms
from django.forms import widgets

from selectable import forms as selectable

from timepiece import utils
from timepiece.utils.search import SearchForm
from timepiece.contracts.models import (EntryGroup, ContractRate, ProjectContract,
    ContractBudget, ContractHour, ContractNote)
from timepiece.crm.models import Attribute
from timepiece.crm.lookups import ProjectLookup, ProjectCodeLookup
from timepiece.entries.models import Activity
from timepiece.forms import DateForm


class InvoiceForm(forms.ModelForm):

    class Meta:
        model = EntryGroup
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


class OutstandingHoursFilterForm(DateForm):
    statuses = forms.ModelMultipleChoiceField(queryset=Attribute.objects.none(),
            required=False, widget=forms.CheckboxSelectMultiple())

    def __init__(self, *args, **kwargs):
        super(OutstandingHoursFilterForm, self).__init__(*args, **kwargs)

        # Check all statuses by default.
        statuses = Attribute.statuses.all()
        self.fields['statuses'].queryset = statuses
        self.fields['statuses'].initial = statuses

        month_start = utils.get_month_start().date()
        self.fields['to_date'].required = True
        self.fields['to_date'].initial = month_start - relativedelta(days=1)
        self.fields['from_date'].initial = None

    def get_from_date(self):
        if self.is_valid():
            return self.cleaned_data['from_date']
        return self.fields['from_date'].initial

    def get_to_date(self):
        if self.is_valid():
            return self.cleaned_data['to_date']
        return self.fields['to_date'].initial

    def get_statuses(self):
        if self.is_valid():
            return self.cleaned_data['statuses']
        return self.fields['statuses'].initial

    def get_form_data(self):
        return {
            'to_date': self.get_to_date(),
            'from_date': self.get_from_date(),
            'statuses': self.get_statuses()
        }

class CreateEditContractRateForm(forms.ModelForm):

    class Meta:
        model = ContractRate
        fields = ('activity', 'rate', 'contract')

    def __init__(self, *args, **kwargs):        
        super(CreateEditContractRateForm, self).__init__(*args, **kwargs)
        self.fields['activity'].choices = [(a.id, a.name) for a in 
            Activity.objects.filter(billable=True).order_by('name')]

class CreateEditContractBudgetForm(forms.ModelForm):

    class Meta:
        model = ContractBudget

class CreateEditContractHourForm(forms.ModelForm):

    class Meta:
        model = ContractHour


class CreateEditContractForm(forms.ModelForm):

    class Meta:
        model = ProjectContract

    def __init__(self, *args, **kwargs):
        super(CreateEditContractForm, self).__init__(*args, **kwargs)
        self.fields['projects'] = selectable.AutoCompleteSelectMultipleField(
            ProjectCodeLookup, required=False, help_text='Search by Project Code.')

class ContractSearchForm(SearchForm):
    status = forms.ChoiceField(required=False, choices=[], label='')

    def __init__(self, *args, **kwargs):
        super(ContractSearchForm, self).__init__(*args, **kwargs)
        statuses = Attribute.statuses.all()
        choices = [('', 'Any Status')] + ProjectContract.CONTRACT_STATUS.items()
        self.fields['status'].choices = choices
        if kwargs.get('data', None) is None:
            self.fields['status'].initial = ProjectContract.STATUS_CURRENT

class AddContractNoteForm(forms.ModelForm):

    class Meta:
        model = ContractNote
        fields = ('text', 'contract', 'author')

    def __init__(self, *args, **kwargs):
        super(AddContractNoteForm, self).__init__(*args, **kwargs)
        self.fields['text'].label = ''
        self.fields['text'].widget.attrs['rows'] = 6
        self.fields['author'].widget = widgets.HiddenInput()
        self.fields['contract'].widget = widgets.HiddenInput()