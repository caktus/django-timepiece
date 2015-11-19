import datetime
from dateutil.relativedelta import relativedelta
import time

from django import forms
from django.contrib.auth.models import User

from timepiece.fields import UserModelChoiceField

from timepiece.entries.models import Entry


DATE_FORM_FORMAT = '%Y-%m-%d'
INPUT_FORMATS = [DATE_FORM_FORMAT]


class TimepieceSplitDateTimeWidget(forms.SplitDateTimeWidget):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('date_format', DATE_FORM_FORMAT)
        super(TimepieceSplitDateTimeWidget, self).__init__(*args, **kwargs)


class TimepieceSplitDateTimeField(forms.SplitDateTimeField):
    widget = TimepieceSplitDateTimeWidget


class TimepieceDateInput(forms.DateInput):

    def __init__(self, *args, **kwargs):
        kwargs['format'] = kwargs.get('format', DATE_FORM_FORMAT)
        super(TimepieceDateInput, self).__init__(*args, **kwargs)


class DateForm(forms.Form):
    from_date = forms.DateField(
        label='From', required=False, input_formats=INPUT_FORMATS,
        widget=TimepieceDateInput())
    to_date = forms.DateField(
        label='To', required=False, input_formats=INPUT_FORMATS,
        widget=TimepieceDateInput())

    def clean(self):
        from_date = self.cleaned_data.get('from_date', None)
        to_date = self.cleaned_data.get('to_date', None)
        if from_date and to_date and from_date > to_date:
            raise forms.ValidationError('The ending date must exceed the '
                                        'beginning date.')
        return self.cleaned_data

    def save(self):
        from_date = self.cleaned_data.get('from_date', '')
        to_date = self.cleaned_data.get('to_date', '')
        to_date = to_date + relativedelta(days=1) if to_date else to_date
        return (from_date, to_date)


class YearMonthForm(forms.Form):
    MONTH_CHOICES = [(i, time.strftime('%b', time.strptime(str(i), '%m')))
                     for i in range(1, 13)]
    month = forms.ChoiceField(choices=MONTH_CHOICES, label='')
    year = forms.ChoiceField(label='')

    def __init__(self, *args, **kwargs):
        super(YearMonthForm, self).__init__(*args, **kwargs)
        now = datetime.datetime.now()
        this_year = now.year
        this_month = now.month
        try:
            first_entry = Entry.no_join.values('end_time')\
                                       .order_by('end_time')[0]
        except IndexError:
            first_year = this_year
        else:
            first_year = first_entry['end_time'].year
        years = [(year, year) for year in range(first_year, this_year + 1)]
        self.fields['year'].choices = years
        initial = kwargs.get('initial')
        if initial:
            this_year = initial.get('year', this_year)
            this_month = initial.get('month', this_month)
        self.fields['year'].initial = this_year
        self.fields['month'].initial = this_month

    def save(self):
        now = datetime.datetime.now()
        this_year = now.year
        this_month = now.month
        month = int(self.cleaned_data.get('month', this_month))
        year = int(self.cleaned_data.get('year', this_year))
        from_date = datetime.datetime(year, month, 1)
        to_date = from_date + relativedelta(months=1)

        return (from_date, to_date)


class UserYearMonthForm(YearMonthForm):
    user = UserModelChoiceField(label='', queryset=None, required=False)

    def __init__(self, *args, **kwargs):
        super(UserYearMonthForm, self).__init__(*args, **kwargs)
        queryset = User.objects.exclude(timepiece_entries=None)\
                               .order_by('first_name')
        self.fields['user'].queryset = queryset

    def save(self):
        from_date, to_date = super(UserYearMonthForm, self).save()
        return (from_date, to_date, self.cleaned_data.get('user', None))
