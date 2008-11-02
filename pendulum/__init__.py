from django.db.models.signals import pre_save
from django.core.exceptions import ValidationError
from pendulum.models import Entry

APP_TITLE = 'Pendulum: Time Clock'

def validate_entry_callback(sender, instance, **kwargs):
    if instance.start_time and instance.end_time:
        if instance.start_time > instance.end_time:
            raise ValidationError('The entry must start before it ends!')

#pre_save.connect(validate_entry_callback, sender=Entry)
