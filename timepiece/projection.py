import datetime
import logging

from django.conf import settings
from django.db.models import Q

from dateutil import rrule
from dateutil import relativedelta

from timepiece import models as timepiece
from timepiece.utils import get_week_start, generate_weeks


logger = logging.getLogger('timepiece.projection')


def contact_weekly_assignments():
    schedules = timepiece.PersonSchedule.objects.all()
    for schedule in schedules:
        last_end_date = schedule.contact.assignments.order_by('-end_date')
        last_end_date = last_end_date.exclude(contract__status='complete')
        last_end_date = last_end_date.values('end_date')[0]['end_date']
        for week in generate_weeks(end=last_end_date):
            next_week = week + relativedelta.relativedelta(weeks=1)
            assignments = schedule.contact.assignments
            q = Q(contract__end_date__gt=next_week)
            q |= Q(contract__end_date__gte=week,
                   contract__end_date__lt=next_week)
            q &= ~Q(contract__project__in=settings.TIMEPIECE_PROJECTS.values())
            assignments = assignments.filter(q)
            yield schedule, week, assignments.order_by('end_date')


def run_projection():
    logger.info('calculating projection')
    timepiece.AssignmentAllocation.objects.all().delete()
    for schedule, week, assignments in contact_weekly_assignments():
        hours_left = schedule.hours_per_week
        for assignment in assignments:
            commitment = assignment.weekly_commitment
            logger.debug('{0} | Remaining Hours: {1:<6.2f} | Commitment: {2:<6.2f} | {3}'.format(week, hours_left, commitment, assignment))
            if commitment > hours_left:
                commitment = hours_left
            hours_left -= commitment
            assignment.blocks.create(date=week, hours=commitment)
            if hours_left <= 0:
                break
    logger.info('projection complete')

