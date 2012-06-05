from django import forms
from timepiece.utils import DEFAULT_TIME_FORMATS


class UserModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_full_name()
