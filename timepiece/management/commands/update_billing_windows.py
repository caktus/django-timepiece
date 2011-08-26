import pprint

from django.conf import settings
from django.db import transaction
from django.core.management.base import NoArgsCommand
from django.core.urlresolvers import reverse

from timepiece import models as timepiece


class Command(NoArgsCommand):
    help = "Generate billing windows"

    @transaction.commit_on_success
    def handle_noargs(self, **options):
        output = []

        projects = timepiece.Project.objects.filter(
            billing_period__active=True
        ).select_related(
            'billing_period',
        )
        for project in projects:
            urls = []
            windows = project.billing_period.update_billing_windows()
            for window in windows:
                url = reverse(
                    'project_time_sheet',
                    args=(project.id, window.id),
                )
                urls.append(settings.APP_URL_BASE + url)
            if urls:
                output.append((project.name, urls))
        if output:
            print 'Project Billing Windows:\n'
            pprint.pprint(output)

        output = []
        prps = timepiece.PersonRepeatPeriod.objects.filter(
            repeat_period__active=True,
        ).select_related(
            'user',
            'repeat_period',
        )
        for prp in prps:
            urls = []
            windows = prp.repeat_period.update_billing_windows()
            for window in windows:
                url = reverse(
                    'view_person_time_sheet',
                    args=(prp.user.id, prp.repeat_period.id, window.id),
                )
                urls.append(settings.APP_URL_BASE + url)
            if urls:
                output.append((prp.user.get_full_name(), urls))

        if output:
            print '\nPerson Time Sheets:\n'
            pprint.pprint(output)
