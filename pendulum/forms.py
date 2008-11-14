from django import forms
from pendulum.models import Project, Activity, Entry
from pendulum.fields import PendulumDateTimeField
from pendulum.widgets import PendulumDateTimeWidget
from datetime import datetime

class ClockInForm(forms.Form):
    """
    Allow users to clock in
    """

    project = forms.ModelChoiceField(queryset=Project.objects.active())

class ClockOutForm(forms.Form):
    """
    Allow users to clock out
    """

    activity = forms.ModelChoiceField(queryset=Activity.objects.all(),
                                      required=False)
    comments = forms.CharField(widget=forms.Textarea,
                               required=False)

class AddUpdateEntryForm(forms.ModelForm):
    """
    This form will provide a way for users to add missed log entries and to
    update existing log entries.
    """

    start_time = forms.DateTimeField(widget=PendulumDateTimeWidget)
    end_time = forms.DateTimeField(widget=PendulumDateTimeWidget)

    #start_time = PendulumDateTimeField()
    #end_time = PendulumDateTimeField()

    class Meta:
        model = Entry
        exclude = ('user', 'seconds_paused', 'pause_time', 'site')

    def clean_start_time(self):
        """
        Make sure that the start time is always before the end time
        """
        start = self.cleaned_data['start_time']

        try:
            end = self.cleaned_data['end_time']

            if start >= end:
                raise forms.ValidationError('The entry must start before it ends!')
        except KeyError:
            pass

        if start > datetime.now():
            raise forms.ValidationError('You cannot add entries in the future!')

        return start

    def clean_end_time(self):
        """
        Make sure no one tries to add entries that end in the future
        """
        try:
            start = self.cleaned_data['start_time']
        except KeyError:
            raise forms.ValidationError('Please enter a start time.')

        try:
            end = self.cleaned_data['end_time']
            if not end: raise Exception
        except:
            raise forms.ValidationError('Please enter an end time.')

        if end > datetime.now():
            raise forms.ValidationError('You cannot clock out in the future!')

        if start >= end:
            raise forms.ValidationError('The entry must start before it ends!')

        return end

    #def clean(self):
    #    print self.cleaned_data
