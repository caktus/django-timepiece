import re
import json
from decimal import Decimal

from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe


re_id = re.compile('id="([^"]+)"')


class DateWidget(forms.TextInput):
    def __init__(self, attrs={}):
        super(DateWidget, self).__init__(attrs={
            'class': 'vDateField', 'size': '10'
        })


class TimeWidget(forms.TextInput):
    def __init__(self, attrs={}):
        super(TimeWidget, self).__init__(attrs={
            'class': 'vTimeField', 'size': '8'
        })


class ToggleBillableWidget(forms.Select):
    def __init__(self, billable, *args, **kwargs):
        self.billable_map = billable
        super(ToggleBillableWidget, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, choices=()):
        output = super(ToggleBillableWidget, self).render(name, value, attrs,
                                                          choices)
        return output + """
        <script type='text/javascript'>
        var billable_map = %s;
        console.log(billable_map);
        jQuery(function() {
            console.log(billable_map);
            jQuery('#id_project').change(function() {
                console.log(billable_map[jQuery(this).val()]);
                jQuery('#id_billable').attr('checked',
                                            billable_map[jQuery(this).val()]);
            });
        });
        </script>
        """ % json.dumps(self.billable_map)
