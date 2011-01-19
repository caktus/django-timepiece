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
    schedules = timepiece.PersonSchedule.objects.select_related()
    for schedule in schedules:
        for week in generate_weeks(end=schedule.furthest_end_date):
            next_week = week + relativedelta.relativedelta(weeks=1)
            assignments = timepiece.ContractAssignment.objects
            assignments = assignments.active_during_week(week, next_week)
            q = Q(contact=schedule.contact)
            q &= ~Q(contract__project__in=settings.TIMEPIECE_PROJECTS.values())
            assignments = assignments.filter(q).select_related()
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

