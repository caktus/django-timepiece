from itertools import groupby

from django.db.models import Sum, Q

from timepiece.utils import add_timezone, get_hours_summary, get_period_start

from timepiece.entries.models import Entry, Activity
from timepiece.crm.models import Project, ActivityGoal, Milestone

from datetime import timedelta

def daily_summary(day_entries):
    projects = {}
    all_day = {}
    for name, entries in groupby(day_entries, lambda x: x['project__name']):
        hours = get_hours_summary(entries)
        projects[name] = hours
        for key in hours.keys():
            if key in all_day:
                all_day[key] += hours[key]
            else:
                all_day[key] = hours[key]
    return (all_day, projects)


def grouped_totals(entries):
    select = {
        "day": {"date": """DATE_TRUNC('day', end_time)"""},
        "week": {"date": """DATE_TRUNC('week', end_time)"""},
    }
    weekly = entries.extra(select=select["week"]).values('date', 'billable')
    weekly = weekly.annotate(hours=Sum('hours')).order_by('date')
    daily = entries.extra(select=select["day"]).values('date', 'project__name',
                                                       'billable')
    daily = daily.annotate(hours=Sum('hours')).order_by('date',
                                                        'project__name')
    weeks = {}
    for week, week_entries in groupby(weekly, lambda x: x['date']):
        # start LOGIC TO SUPPORT SUN-SAT WEEK
        week -= timedelta(days=1)
        # end LOGIC TO SUPPORT SUN-SAT WEEK
        if week is not None:
            week = add_timezone(week)
        weeks[week] = get_hours_summary(week_entries)
    
    # start LOGIC TO SUPPORT SUN-SAT WEEK
    # TODO: for some reason aggregate is not working, so this needs to be
    # improved
    for week, totals in weeks.items():
        next_sun = week + timedelta(days=7)
        start_sun_b_entries = entries.filter(end_time__contains=week.date(),
            activity__billable=True)
        start_sun_nb_entries = entries.filter(end_time__contains=week.date(),
            activity__billable=False)
        next_sun_b_entries = entries.filter(end_time__contains=next_sun.date(),
            activity__billable=True)
        next_sun_nb_entries = entries.filter(end_time__contains=next_sun.date(),
            activity__billable=False)
        
        start_sun_b = 0
        start_sun_nb = 0
        end_sun_b = 0
        end_sun_nb = 0
        for e in start_sun_b_entries:
            start_sun_b += e.hours
        for e in start_sun_nb_entries:
            start_sun_nb += e.hours
        for e in next_sun_b_entries:
            end_sun_b += e.hours
        for e in next_sun_nb_entries:
            end_sun_nb += e.hours
        
        weeks[week]['billable'] += (start_sun_b - end_sun_b)
        weeks[week]['non_billable'] += (start_sun_nb - end_sun_nb)
        weeks[week]['total'] = weeks[week]['billable'] + weeks[week]['non_billable']
    # end LOGIC TO SUPPORT SUN-SAT WEEK
    
    days = []
    last_week = None
    for day, day_entries in groupby(daily, lambda x: x['date']):
        week = get_period_start(day)
        if last_week and week > last_week:
            yield last_week, weeks.get(last_week, {}), days
            days = []
        days.append((day, daily_summary(day_entries)))
        last_week = week

    yield week, weeks.get(week, {}), days
# from django.db.models import Q
def project_activity_goals_with_progress(project):
    activity_goals = {}
    for employee, ags in groupby(ActivityGoal.objects.filter(project=project).order_by('employee', 'activity'), lambda ag: ag.employee):
        if employee is None:
            key = 'No Employee Assigned'
        else:
            key = employee.username
        
        if key not in activity_goals:
            activity_goals[key] = []

        exclude_Q = Q()
        for ag in ags:
            # WILL CHANGE SO employee IS NOT NONE
            if employee is None:
                # first, need to find list of employees that have an activity goal for this project of this activity
                users_with_goals = [temp_ag.employee for temp_ag in ActivityGoal.objects.filter(project=ag.project, activity=ag.activity).exclude(employee=None)]
                charged_hours = Entry.objects.filter(project=project, activity=ag.activity
                    ).exclude(user__in=users_with_goals
                    ).aggregate(Sum('hours'))['hours__sum'] or 0.0
                if ag.activity:
                    ag_name = ag.activity.name
                else:
                    ag_name = 'Other'
            else:
                if ag.activity:
                    charged_hours = Entry.objects.filter(
                        project=project, user=employee, activity=ag.activity
                        ).aggregate(Sum('hours'))['hours__sum'] or 0.0
                    ag_name = ag.activity.name
                    exclude_Q |= Q(activity=ag.activity)
                else:
                    # NEED TO GET RID OF THIS
                    charged_hours = Entry.objects.filter(project=project, user=employee
                        ).exclude(Q(activity__id=12)|Q(activity__id=17)|Q(activity__id=11)).aggregate(Sum('hours'))['hours__sum'] or 0
                    ag_name = 'Other'
            remaining_hours = float(ag.goal_hours) - float(charged_hours)
            percentage = 100.*(float(charged_hours)/float(ag.goal_hours)) if float(ag.goal_hours) > 0 else 0
            percentage = 100 if float(ag.goal_hours)==0.0 else percentage
            activity_goals[key].append({'id': ag.id,
                                        'activity': ag.activity,
                                        'activity_name': ag_name,
                                        'project': project,
                                        'employee': employee,
                                        'hours': float(ag.goal_hours),
                                        'charged_hours': float(charged_hours),
                                        'remaining_hours': remaining_hours,
                                        'percentage': percentage})
        
        for activity_sum in Entry.objects.filter(project=project, user=employee
            ).exclude(exclude_Q).values('activity'
            ).annotate(hours=Sum('hours')).order_by('-hours'):

            activity = Activity.objects.get(id=activity_sum['activity'])

            activity_goals[key].append({'id': None,
                                        'activity': activity,
                                        'activity_name': activity.name,
                                        'project': project,
                                        'employee': employee,
                                        'hours': 0.0,
                                        'charged_hours': activity_sum['hours'],
                                        'remaining_hours': -1*activity_sum['hours'],
                                        'percentage': 100.0})

    return activity_goals
