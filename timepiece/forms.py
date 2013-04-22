import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import time

from django import forms
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from selectable import forms as selectable

from timepiece.crm.lookups import QuickLookup
from timepiece.fields import UserModelChoiceField

from timepiece.entries.models import Entry


DATE_FORM_FORMAT = '%Y-%m-%d'


class QuickSearchForm(forms.Form):
    quick_search = selectable.AutoCompleteSelectField(
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
            return reverse('view_user', args=(pk,))
        elif type == 'business':
            return reverse('view_business', args=(pk,))
        elif type == 'project':
            return reverse('view_project', args=(pk,))

        raise forms.ValidationError('Must be a user, project, or business')


class DateForm(forms.Form):
    DATE_FORMAT = DATE_FORM_FORMAT

    from_date = forms.DateField(label='From', required=False,
        input_formats=(DATE_FORMAT,),
        widget=forms.DateInput(format=DATE_FORMAT))
    to_date = forms.DateField(label='To', required=False,
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
    MONTH_CHOICES = [(i, time.strftime('%b', time.strptime(str(i), '%m')))
                     for i in xrange(1, 13)]
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
        years = [(year, year) for year in xrange(first_year, this_year + 1)]
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


class SearchForm(forms.Form):
    search = forms.CharField(required=False, label='')
    search.widget.attrs['placeholder'] = 'Search'

    def save(self):
        search = self.cleaned_data.get('search', '')
        return search
