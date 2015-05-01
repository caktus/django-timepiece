from django import forms
from django.utils.html import mark_safe


class UserModelChoiceField(forms.ModelChoiceField):

    def label_from_instance(self, obj):
        return obj.get_name_or_username()


class UserModelMultipleChoiceField(forms.ModelMultipleChoiceField):

    def label_from_instance(self, obj):
        return obj.get_name_or_username()

class WeeklyScheduleWidget(forms.MultiWidget):

    def __init__(self, attrs=None):
        _widgets = (
            forms.widgets.TextInput(attrs=attrs), 
            forms.widgets.TextInput(attrs=attrs),
            forms.widgets.TextInput(attrs=attrs),
            forms.widgets.TextInput(attrs=attrs),
            forms.widgets.TextInput(attrs=attrs),
            forms.widgets.TextInput(attrs=attrs),
            forms.widgets.TextInput(attrs=attrs),
            )
        super(WeeklyScheduleWidget, self).__init__(_widgets, attrs)

    def decompress(self, value):
        if value:
            return [float(val) for val in value.split(',')]
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    def render(self, name, value, attrs=None):
        html = '<table style="width: 0;" class="table table-bordered">' \
             + '<thead>' \
             + '<th>Sunday</th>' \
             + '<th>Monday</th>' \
             + '<th>Tuesday</th>' \
             + '<th>Wednesday</th>' \
             + '<th>Thursday</th>' \
             + '<th>Friday</th>' \
             + '<th>Saturday</th>' \
             + '</thead><tbody><tr>'
        for idx, val in enumerate(self.decompress(value)):
            html += '<td><input id="id_weekly_schedule_%d" name="weekly_schedule_%d" type="number" step="any" min="0" value="%.2f" style="width: 50px;" /></td>' % (idx, idx, val)
        html += '</tr></tbody></table>'
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        vals = []
        for i in range(7):
            val = data.get('weekly_schedule_%d' % i, 0.0)
            vals.append(val if val else '0.0')
        return ','.join(vals)
