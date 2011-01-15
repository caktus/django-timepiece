import datetime

from django.conf import settings

from dateutil import rrule

from timepiece import models as timepiece


def run_projection():
    timepiece.ContractBlock.objects.all().delete()
    contracts = timepiece.ProjectContract.objects.exclude(status='complete')
    for contract in contracts:
        weekdays = rrule.rrule(rrule.DAILY, dtstart=contract.start_date,
                               until=contract.end_date - datetime.timedelta(days=1), byweekday=range(0, 5))
        assignments = contract.assignments.exclude(contract__project__in=settings.TIMEPIECE_PROJECTS.values())
        for assignment in assignments:
            hours = assignment.hours_remaining/weekdays.count()
            for weekday in weekdays:
                assignment.blocks.create(date=weekday, hours=hours) 

