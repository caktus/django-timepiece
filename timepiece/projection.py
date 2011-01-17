import datetime

from django.conf import settings

from dateutil import rrule

from timepiece import models as timepiece


def run_projection():
    timepiece.ContractBlock.objects.all().delete()
    contracts = timepiece.ProjectContract.objects.exclude(status='complete')
    for contract in contracts:
        until = contract.end_date - datetime.timedelta(days=1)
        weeks = rrule.rrule(rrule.WEEKLY, dtstart=contract.start_date,
                            until=until, byweekday=6)
        
        exclude = {'contract__project__in': settings.TIMEPIECE_PROJECTS.values()}
        assignments = contract.assignments.exclude(**exclude)
        for assignment in assignments:
            hours = assignment.hours_remaining/weeks.count()
            for week in weeks:
                assignment.blocks.create(date=week, hours=hours) 

