from django import forms
from timepiece.widgets import PendulumDateTimeWidget
from timepiece.utils import DEFAULT_TIME_FORMATS


class PendulumDateTimeField(forms.SplitDateTimeField):
    """
    This custom field is just a way to offer some more friendly ways to enter
    a time, such as 1pm or 8:15 pm
    """
    widget = PendulumDateTimeWidget

    def __init__(self, date_formats=None, time_formats=None, help_text=None,
        *args, **kwargs):
        time_formats = time_formats or DEFAULT_TIME_FORMATS
        fields = (
            forms.fields.DateField(input_formats=date_formats),
            forms.fields.TimeField(input_formats=time_formats))
        forms.MultiValueField.__init__(self, fields, help_text=help_text,
            *args, **kwargs)
