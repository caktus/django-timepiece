import datetime
import logging

from django.conf import settings
from django.db.models import Q

from dateutil import rrule
from dateutil import relativedelta

from timepiece import models as timepiece
from timepiece.utils import get_week_start, generate_dates


logger = logging.getLogger('timepiece.projection')


def user_weekly_assignments():
    schedules = timepiece.PersonSchedule.objects.select_related()
    for schedule in schedules:
        for week in generate_dates(end=schedule.furthest_end_date, by='week'):
            next_week = week + relativedelta.relativedelta(weeks=1)
            assignments = timepiece.ContractAssignment.objects
            assignments = assignments.active_during_week(week, next_week)
            q = Q(user=schedule.user)
            q &= ~Q(contract__project__in=settings.TIMEPIECE_PROJECTS.values())
            assignments = assignments.filter(q).select_related()
            yield schedule, week, assignments.order_by('end_date')


def run_projection():
    logger.info('calculating projection')
    timepiece.AssignmentAllocation.objects.all().delete()
    for schedule, week, assignments in user_weekly_assignments():
        for assignment in assignments:
            commitment = assignment.weekly_commitment(week)
            assignment.blocks.create(date=week, hours=commitment)
            logger.debug('{0} | Commitment: {1:<6.2f} | {2}'.format(
                week, commitment, assignment))
            # if hours_left <= 0:
            #     break
    logger.info('projection complete')
