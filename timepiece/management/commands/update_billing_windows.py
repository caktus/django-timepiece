import pprint

from django.conf import settings
from django.db import transaction
from django.core.management.base import NoArgsCommand
from django.core.urlresolvers import reverse

from timepiece.models import RepeatPeriod


class Command(NoArgsCommand):
    help = "Generate billing windows"
    
    @transaction.commit_on_success
    def handle_noargs(self, **options):
        urls = []
        for period, windows in RepeatPeriod.objects.update_billing_windows():
            for window in windows:
                url = reverse(
                    'project_time_sheet',
                    args=(period.project.id, window.id),
                )
                urls.append(settings.APP_URL_BASE+url)
        if urls:
            print 'The following billing windows were created:'
            pprint.pprint(urls)
