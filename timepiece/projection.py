from dateutil import rrule

from timepiece import models as timepiece


def run_projection():
    timepiece.ContractBlock.objects.all().delete()
    contracts = timepiece.ProjectContract.objects.filter(status='current')
    for contract in contracts:
        weekdays = rrule.rrule(rrule.DAILY, dtstart=contract.start_date,
                               until=contract.end_date, byweekday=range(0, 5))
        for assignment in contract.assignments.all():
            hours = assignment.hours_remaining/weekdays.count()
            for weekday in weekdays:
                assignment.blocks.create(date=weekday, hours=hours) 

