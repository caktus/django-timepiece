import datetime
import logging

from django.conf import settings
from django.db.models import Q

from dateutil import rrule
from dateutil import relativedelta

from timepiece import models as timepiece


logger = logging.getLogger('timepiece.projection')


def contact_weekly_assignments():
    today = datetime.datetime.today()
    schedules = timepiece.PersonSchedule.objects.all()
    for schedule in schedules:
        until = schedule.end_date - datetime.timedelta(days=1)
        weeks = rrule.rrule(rrule.WEEKLY, dtstart=today,
                            until=until, byweekday=6)
        for week in weeks:
            next_week = week + relativedelta.relativedelta(weeks=1)
            assignments = schedule.contact.assignments
            q = Q(contract__end_date__gt=next_week)
            q |= Q(contract__end_date__gte=week,
                   contract__end_date__lt=next_week)
            q &= Q(contract__start_date__lte=week)
            q &= ~Q(contract__project__in=settings.TIMEPIECE_PROJECTS.values())
            assignments = assignments.filter(q)
            yield schedule, week, assignments.order_by('end_date')


def run_projection():
    logger.info('calculating projection')
    timepiece.ContractBlock.objects.all().delete()
    for schedule, week, assignments in contact_weekly_assignments():
        hours_left = schedule.hours_per_week
        for assignment in assignments:
            logger.debug('{0} {1}'.format(week, assignment))
            commitment = assignment.weekly_commitment
            if commitment > hours_left:
                commitment = hours_left
            hours_left -= commitment
            assignment.blocks.create(date=week, hours=commitment)
            if hours_left <= 0:
                break
    logger.info('projection complete')

