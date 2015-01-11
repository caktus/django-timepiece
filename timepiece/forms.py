import datetime
from dateutil.relativedelta import relativedelta
import time
import calendar

from django import forms
from django.contrib.auth.models import User

from timepiece.fields import UserModelChoiceField

from timepiece.entries.models import Entry


DATE_FORM_FORMAT = '%Y-%m-%d'
INPUT_FORMATS = [DATE_FORM_FORMAT]


class TimepieceSplitDateTimeWidget(forms.SplitDateTimeWidget):

    def __init__(self, *args, **kwargs):
        kwargs['date_format'] = kwargs.get('date_format', DATE_FORM_FORMAT)
        super(TimepieceSplitDateTimeWidget, self).__init__(*args, **kwargs)


class TimepieceDateInput(forms.DateInput):

    def __init__(self, *args, **kwargs):
        kwargs['format'] = kwargs.get('format', DATE_FORM_FORMAT)
        super(TimepieceDateInput, self).__init__(*args, **kwargs)


class DateForm(forms.Form):
    from_date = forms.DateField(label='From', required=False,
        input_formats=INPUT_FORMATS, widget=TimepieceDateInput())
    to_date = forms.DateField(label='To', required=False,
        input_formats=INPUT_FORMATS, widget=TimepieceDateInput())

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

class UserDateForm(DateForm):
    user = UserModelChoiceField(label='', queryset=None, required=False)

    def __init__(self, *args, **kwargs):
        super(UserDateForm, self).__init__(*args, **kwargs)
        queryset = User.objects.exclude(timepiece_entries=None)\
                               .order_by('first_name')
        self.fields['user'].queryset = queryset
        self.fields['to_date'].label = ''
        self.fields['to_date'].widget.attrs['placeholder'] = 'End Date'
        self.fields['from_date'].label = ''
        self.fields['from_date'].widget.attrs['placeholder'] = 'Start Date'

    def save(self):
        from_date, to_date = super(UserDateForm, self).save()
        return (from_date, to_date, self.cleaned_data.get('user', None))

class StatusDateForm(DateForm):
    status = forms.ChoiceField(label='', required=False)

    def __init__(self, *args, **kwargs):
        super(StatusDateForm, self).__init__(*args, **kwargs)
        self.fields['status'].choices = [('', 'All')] + Entry.STATUSES.items()

    def save(self):
        (from_date, to_date) = super(StatusDateForm, self).save()
        return (from_date, to_date, self.cleaned_data.get('status', None))

class StatusUserDateForm(UserDateForm):
    status = forms.ChoiceField(label='', required=False)

    def __init__(self, *args, **kwargs):
        super(StatusUserDateForm, self).__init__(*args, **kwargs)
        self.fields['status'].choices = [('', 'All')] + Entry.STATUSES.items()

    def save(self):
        (from_date, to_date, user) = super(StatusUserDateForm, self).save()
        return (from_date, to_date, user, self.cleaned_data.get('status', None))


class YearMonthForm(forms.Form):
    MONTH_CHOICES = [(i, time.strftime('%b', time.strptime(str(i), '%m')))
                     for i in xrange(1, 13)]
    #MONTH_CHOICES = sum([[(2*i-1, time.strftime('%b', time.strptime(str(i), '%m'))+' 1-15'), (2*i, time.strftime('%b', time.strptime(str(i), '%m'))+' 16-'+str(calendar.monthrange(datetime.datetime.now().year,i)[1]))] for i in xrange(1, 13)], [])
    month = forms.ChoiceField(choices=MONTH_CHOICES, label='')
    half = forms.ChoiceField(choices=[(1, '1st - 15th'), (2, '16th - end')], label='')
    year = forms.ChoiceField(label='')

    def __init__(self, *args, **kwargs):
        super(YearMonthForm, self).__init__(*args, **kwargs)
        now = datetime.datetime.now()
        this_year = now.year
        this_month = now.month
        this_half = 1 if datetime.datetime.now().day <= 15 else 2
        try:
            first_entry = Entry.no_join.values('end_time')\
                                       .order_by('end_time')[0]
        except IndexError:
            first_year = this_year
        else:
            first_year = first_entry['end_time'].year
        years = [(year, year) for year in xrange(first_year, this_year + 1)]
        self.fields['year'].choices = years
        initial = kwargs.get('initial')
        print 'initial', initial
        if initial:
            this_year = initial.get('year', this_year)
            this_month = initial.get('month', this_month)
            this_half = initial.get('half', this_half)
            print 'this_month', this_month
        self.fields['year'].initial = this_year
        self.fields['month'].initial = this_month
        self.fields['half'].initial = this_half

    def save(self):
        now = datetime.datetime.now()
        this_year = now.year
        this_month = now.month
        this_half = 1 if datetime.datetime.now().day <= 15 else 2
        print 'self.cleaned_data', self.cleaned_data
        month = int(self.cleaned_data.get('month', this_month))
        year = int(self.cleaned_data.get('year', this_year))
        half = int(self.cleaned_data.get('half', this_half))
        if half == 1:
            from_date = datetime.datetime(year, month, 1)
            to_date = datetime.datetime(year, month, 16)
        elif half == 2:
            from_date = datetime.datetime(year, month, 16)
            if month<12:
                to_date = datetime.datetime(year, month+1,1)
            else:
                to_date = datetime.datetime(year+1, 1,1)

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
