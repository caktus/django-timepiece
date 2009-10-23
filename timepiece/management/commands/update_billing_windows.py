from django.core.management.base import NoArgsCommand
from django.db import transaction
from django.contrib.auth.models import User

from timepiece import models as timepiece

class Command(NoArgsCommand):
    help = "Update billing windows"
    
    @transaction.commit_on_success
    def handle_noargs(self, **options):
        for repeat_period in timepiece.RepeatPeriod.objects.filter(active=True):
            windows = repeat_period.update_billing_windows()
            print repeat_period, windows
