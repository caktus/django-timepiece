from dateutil.relativedelta import relativedelta

from django import forms

from timepiece import utils
from timepiece.contracts.models import EntryGroup
from timepiece.crm.models import Attribute
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
    statuses = forms.ModelMultipleChoiceField(
        queryset=Attribute.objects.none(), required=False,
        widget=forms.CheckboxSelectMultiple())

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
