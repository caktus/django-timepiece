import datetime
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from itertools import groupby
import workdays

from timepiece.utils import get_hours_summary, add_timezone, get_week_start,\
        get_month_start, get_year_start, get_setting, get_bimonthly_dates
from timepiece.entries.models import Entry

from django.contrib.auth.models import User, Group
from django.db.models import Sum, Q, Min, Max

from timepiece.crm.models import ActivityGoal, PaidTimeOffRequest, Project, Attribute, Business, UserProfile
from timepiece.entries.models import Activity, Entry

from holidays.models import Holiday


def date_totals(entries, by):
    """Yield a user's name and a dictionary of their hours"""
    date_dict = {}
    for date, date_entries in groupby(entries, lambda x: x['date']):
        if isinstance(date, datetime.datetime):
            date = date.date()
        d_entries = list(date_entries)

        if by == 'user':
            name = ', '.join((d_entries[0]['user__last_name'],
                    d_entries[0]['user__first_name']))
        elif by == 'project':
            name = '%s: %s' % (d_entries[0]['project__code'], d_entries[0]['project__name'])
        else:
            name = d_entries[0][by]

        pk = d_entries[0][by]
        hours = get_hours_summary(d_entries)
        if date in date_dict:
            for entry_type in ['total', 'billable', 'non_billable']:
                date_dict[date][entry_type] += hours[entry_type]
        else:
            date_dict[date] = hours
    return name, pk, date_dict


def find_overtime(dates):
    """Given a list of weekly summaries, return the overtime for each week"""
    return sum([day - 40 for day in dates if day > 40])

def find_correct_overtime(from_date, to_date, user, weeks):
    """For pay periods that do not align with weeks, need more complicated
    logic for determining overtime."""
    paid_leave = get_setting('TIMEPIECE_PAID_LEAVE_PROJECTS')
    unpaid_leave = get_setting('TIMEPIECE_UNPAID_LEAVE_PROJECTS')
    total_overtime = 0.0
    for week in weeks:
        end_of_week = week + relativedelta(days=7, microseconds=-1)
        if end_of_week >= from_date and end_of_week < to_date:
            entries = Entry.objects.filter(user=user, end_time__gte=week,
                end_time__lt=end_of_week
                ).exclude(project__in=paid_leave.values()
                ).exclude(project__in=unpaid_leave.values())
            if entries.count() == 0:
                continue
            
            week_total = float(entries.aggregate(
                hours=Sum('hours'))['hours'])
            if week_total > 40.0:
                total_overtime += (week_total - 40.0)

    return total_overtime


def generate_dates(start=None, end=None, by='week'):
    if start:
        start = add_timezone(start)
    if end:
        end -= datetime.timedelta(microseconds=1)
        end = add_timezone(end)

    week_start = get_setting('TIMEPIECE_WEEK_START', default=0)
    if by == 'year':
        start = get_year_start(start)
        return rrule.rrule(rrule.YEARLY, dtstart=start, until=end)
    if by == 'month':
        start = get_month_start(start)
        return rrule.rrule(rrule.MONTHLY, dtstart=start, until=end)
    if by == 'week':
        start = get_week_start(start)
        return rrule.rrule(rrule.WEEKLY, dtstart=start, until=end, byweekday=week_start)
    if by == 'day':
        return rrule.rrule(rrule.DAILY, dtstart=start, until=end)


def get_project_totals(entries, date_headers, hour_type=None, overtime=False,
                   total_column=False, by='user', writedown=None,
                   from_date=None, to_date=None):
    """
    Yield hour totals grouped by user and date. Optionally including overtime.
    """
    if writedown is not None:
        try:
            entries = entries.filter(writedown=writedown)
        except:
            filtered_entries = []
            for entry in entries:
                if entry['writedown'] == writedown:
                    filtered_entries.append(entry)
            entries = filtered_entries
    totals = [0 for date in date_headers]
    rows = []
    for thing, thing_entries in groupby(entries, lambda x: x[by]):
        name, thing_id, date_dict = date_totals(thing_entries, by)
        dates = []
        for index, day in enumerate(date_headers):
            if isinstance(day, datetime.datetime):
                day = day.date()
            if hour_type:
                total = date_dict.get(day, {}).get(hour_type, 0)
                dates.append(total)
            else:
                billable = date_dict.get(day, {}).get('billable', 0)
                nonbillable = date_dict.get(day, {}).get('non_billable', 0)
                total = billable + nonbillable
                dates.append({
                    'day': day,
                    'billable': billable,
                    'nonbillable': nonbillable,
                    'total': total
                })
            totals[index] += total
        if total_column:
            dates.append(sum(dates))
        if overtime:
            #dates.append(find_overtime(dates)) # this is the old wrong method
            if by == 'user' and from_date is not None and to_date is not None:
                user = User.objects.get(id=thing)
                weeks = [date for date in date_headers]
                dates.append(find_correct_overtime(
                    add_timezone(from_date), add_timezone(to_date),
                    user, weeks)
                )
        dates = [date or '' for date in dates]
        rows.append((name, thing_id, dates))
    if total_column:
        totals.append(sum(totals))
    totals = [t or '' for t in totals]
    yield (rows, totals)


def get_payroll_totals(month_work_entries, month_leave_entries):
    """Summarizes monthly work and leave totals, grouped by user.

    Returns (labels, rows).
        labels -> {'billable': [proj_labels], 'nonbillable': [proj_labels]}
        rows -> [{
            name: name of user,
            billable, nonbillable, leave: [
                {'hours': hours for label, 'percent': % of work or leave total}
            ],
            work_total: sum of billable and nonbillable hours,
            leave_total: sum of leave hours
            grand_total: sum of work_total and leave_total
        }]

    The last entry in each of the billable/nonbillable/leave lists contains a
    summary of the status. The last row contains sum totals for all other rows.
    """
    def _get_user_info(entries):
        """Helper for getting the associated user's first and last name."""
        fname = entries[0].get('user__first_name', '') if entries else ''
        lname = entries[0].get('user__last_name', '') if entries else ''
        name = '{1}, {0}'.format(fname, lname).strip()
        user_id = entries[0].get('user', None) if entries else None
        return {'name': name, 'user_id': user_id}

    def _get_index(status, label):
        """
        Returns the index in row[status] (where row is the row corresponding
        to the current user) where hours for the project label should be
        recorded.

        If the label does not exist, then it is added to the labels list.
        Each row and the totals row is updated accordingly.

        Requires that labels, rows, and totals are in scope.
        """
        if label in labels[status]:
            return labels[status].index(label)
        # Otherwise: update labels, rows, and totals to reflect the addition.
        labels[status].append(label)
        for row in rows:
            row[status].insert(-1, {'hours': Decimal(), 'percent': Decimal()})
        totals[status].insert(-1, {'hours': Decimal(), 'percent': Decimal()})
        return len(labels[status]) - 1

    def _construct_row(name, user_id=None):
        """Constructs an empty row for the given name."""
        row = {'name': name, 'user_id': user_id}
        for status in labels.keys():
            # Include an extra entry for summary.
            row[status] = [{'hours': Decimal(), 'percent': Decimal()}
                           for i in range(len(labels[status]) + 1)]
        row['work_total'] = Decimal()
        row['grand_total'] = Decimal()
        return row

    def _add_percentages(row, statuses, total):
        """For each entry in each status, percent = hours / total"""
        if total:
            for status in statuses:
                for i in range(len(row[status])):
                    p = row[status][i]['hours'] / total * 100
                    row[status][i]['percent'] = p

    def _get_sum(row, statuses):
        """Sum the number of hours worked in given statuses."""
        return sum([row[status][-1]['hours'] for status in statuses])

    work_statuses = ('billable', 'nonbillable')
    leave_statuses = ('leave', )
    labels = dict([(status, []) for status in work_statuses + leave_statuses])
    rows = []
    totals = _construct_row('Totals')
    user_ids = set([e['user'] for e in month_work_entries] + 
        [e['user'] for e in month_leave_entries])
    users = [u.id for u in User.objects.filter(id__in=user_ids
        ).order_by('last_name', 'first_name', 'id')]
    
    # for user, work_entries in groupby(month_work_entries, lambda e: e['user']):
    for user in users:
        work_entries = list(month_work_entries.filter(user=user))
        leave_entries = month_leave_entries.filter(user=user)
        if len(work_entries):
            row = _construct_row(**_get_user_info(work_entries))
        else:
            row = _construct_row(**_get_user_info(leave_entries))

        rows.append(row)
        for entry in work_entries:
            status = 'billable' if entry['billable'] else 'nonbillable'
            label = entry['project__type__label']
            index = _get_index(status, label)
            hours = entry['hours']
            row[status][index]['hours'] += hours
            row[status][-1]['hours'] += hours
            totals[status][index]['hours'] += hours
            totals[status][-1]['hours'] += hours

        status = 'leave'
        for entry in leave_entries:
            label = entry.get('project__name')
            index = _get_index(status, label)
            hours = entry.get('hours')
            row[status][index]['hours'] += hours
            row[status][-1]['hours'] += hours
            totals[status][index]['hours'] += hours
            totals[status][-1]['hours'] += hours

        row['work_total'] = _get_sum(row, work_statuses)
        _add_percentages(row, work_statuses, row['work_total'])
        row['leave_total'] = _get_sum(row, leave_statuses)
        _add_percentages(row, leave_statuses, row['leave_total'])
        row['grand_total'] = row['work_total'] + row['leave_total']

    totals['work_total'] = _get_sum(totals, work_statuses)
    _add_percentages(totals, work_statuses, totals['work_total'])
    totals['leave_total'] = _get_sum(totals, leave_statuses)
    _add_percentages(totals, leave_statuses, totals['leave_total'])
    totals['grand_total'] = totals['work_total'] + totals['leave_total']

    if rows:
        rows.append(totals)
    return labels, rows


def get_week_window(day=None):
    """Returns (Monday, Sunday) of the requested week."""
    start = get_week_start(day)
    return (start, start + relativedelta(days=6))

def get_week_trunc_sunday(date):
    if date.weekday() < 6:
        return date - datetime.timedelta(date.weekday()+1)
    else:
        return date

# accepted answer from
# http://stackoverflow.com/questions/1143671/python-sorting-list-of-dictionaries-by-multiple-keys
# a = multikeysort(b, ['-Total_Points', 'TOT_PTS_Misc'])
def multikeysort(items, columns):
    from operator import itemgetter
    comparers = [ ((itemgetter(col[1:].strip()), -1) if col.startswith('-') else (itemgetter(col.strip()), 1)) for col in columns]  
    def comparer(left, right):
        for fn, mult in comparers:
            result = cmp(fn(left), fn(right))
            if result:
                return mult * result
        else:
            return 0
    return sorted(items, cmp=comparer)

def get_company_backlog_chart_data(activity_goalQ):
    """
    Creates the data objects required by the c3 frond-end visualization
    """

    employees = Group.objects.get(id=1).user_set.filter(is_active=True).order_by('last_name', 'first_name')
    hours_per_week = Decimal('0.0')
    for employee in employees:
        hours_per_week += Decimal(employee.profile.hours_per_week)
    
    coverage = {}

    # start_week = get_week_start(datetime.date.today()).date()
    start_week = datetime.date.today()
    activity_goals = ActivityGoal.objects.filter(activity_goalQ,
        employee__in=employees, end_date__gte=start_week
        ).order_by('project__code', 'activity__name')

    if activity_goals.count() == 0:
         return {}, {}

    include_timeoff = True
    try:
        pto_project = get_setting('TIMEPIECE_PTO_PROJECT')
        upto_project = get_setting('TIMEPIECE_UPTO_PROJECT')
        holiday_project = get_setting('TIMEPIECE_HOLIDAY_PROJECT')
        projects = [ag.project.id for ag in activity_goals]
        if pto_project in pojects and upto_project in projects and holiday_project in projects:
            include_timeoff = True
        else:
            include_timeoff = False
    except:
        include_timeoff = False


    # determine the end date and add one more week to show clearly that
    # the company has no coverage then
    end_date = max(
        get_bimonthly_dates(datetime.date.today())[1].date(),
        activity_goals.aggregate(end_date=Max('end_date'))['end_date'])
    end_week = get_week_start(end_date).date() \
              + datetime.timedelta(days=7)

    # get total number of weeks shown on plot; this equals the
    # length of the arrays
    num_weeks = (end_week - start_week).days / 7.0 + 1

    if include_timeoff:
        # determine holidays and add time (whether paid or not)
        holidays = [h['date'] for h in Holiday.holidays_between_dates(
            start_week, end_week, {'paid_holiday': True})]
        for holiday in holidays:
            if str(holiday) not in coverage:
                coverage[str(holiday)] = {}
            coverage[str(holiday)]['Holiday'] = float(hours_per_week / Decimal('5.0'))

        # add Time Off requests as holidays
        # TODO: should make this smarter so that if it is a partial day it
        #       does not count as a full day
        userprofiles = [employee.profile for employee in employees]
        for ptor in PaidTimeOffRequest.objects.filter(
            Q(user_profile__in=userprofiles),
            Q(pto_start_date__gte=start_week)|Q(pto_end_date__gte=end_week),
            Q(status='approved')|Q(status='processed')):
            
            num_workdays = max(workdays.networkdays(ptor.pto_start_date, 
                ptor.pto_end_date, holidays), 1)
            ptor_hours_per_day = ptor.amount / Decimal(num_workdays)

            for i in range((ptor.pto_end_date-ptor.pto_start_date).days + 1):
                date = ptor.pto_start_date + datetime.timedelta(days=i)
                if date.weekday() < 5:
                    # holidays.append(date) # this is causing issues by not counting as
                    if str(date) not in coverage:
                        coverage[str(date)] = {}
                    coverage[str(date)]['Approved Time Off'] = \
                        float(ptor_hours_per_day)

        y_axes = {'Holiday': ['data1'],
                  'Approved Time Off': ['data2']}
        data_counter = 3
    
        chart_filters = {'Holiday': {
                            'project-type': 8,
                            'project-status': 4,
                            'billable': False,
                            'client': 6},
                         'Approved Time Off': {
                            'project-type': 8,
                            'project-status': 4,
                            'billable': False,
                            'client': 6}
                        }
        export_filters = {'Holiday': {
                            'project-type': Attribute.objects.get(id=8),
                            'project-status': Attribute.objects.get(id=4),
                            'billable': False,
                            'client': Business.objects.get(id=6),
                            'activity': Activity.objects.get(id=25),
                            'project': Project.objects.get(id=354)},
                         'Approved Time Off': {
                            'project-type': Attribute.objects.get(id=8),
                            'project-status': Attribute.objects.get(id=4),
                            'billable': False,
                            'client': Business.objects.get(id=6),
                            'activity': Activity.objects.get(id=24),
                            'project': Project.objects.get(id=245)}
                        }
    else:
        y_axes = {}
        data_counter = 1
        chart_filters = {}
        export_filters = {}
        holidays = [h['date'] for h in Holiday.holidays_between_dates(
            start_week, end_week, {'paid_holiday': True})]
    
    project_statuses = []
    project_types = []
    clients = []
    billable = []
    for activity_goal in activity_goals:
        key = '%s - %s' % (activity_goal.project.code, activity_goal.activity.name)
        if key not in chart_filters:
            project_types.append(activity_goal.project.type)
            project_statuses.append(activity_goal.project.status)
            clients.append(activity_goal.project.business)
            billable.append(activity_goal.project.type.billable and activity_goal.activity.billable)
            chart_filters[key] = {
                'project-type': activity_goal.project.type.id,
                'project-status': activity_goal.project.status.id,
                'billable': activity_goal.project.type.billable and activity_goal.activity.billable,
                'client': activity_goal.project.business.id}
            export_filters[key] = {
                'project-type': activity_goal.project.type,
                'project-status': activity_goal.project.status,
                'billable': activity_goal.project.type.billable and activity_goal.activity.billable,
                'client': activity_goal.project.business,
                'activity': activity_goal.activity,
                'project': activity_goal.project}

        start_date = start_week if activity_goal.date < start_week \
            else activity_goal.date
        
        end_date = activity_goal.end_date
        num_workdays = max(workdays.networkdays(start_date, end_date, 
            holidays), 1)
        ag_hours_per_workday = activity_goal.get_remaining_hours / Decimal(num_workdays)

        for i in range((end_date-start_date).days + 1):
            date = start_date + datetime.timedelta(days=i)
            if workdays.networkdays(date, date, holidays):
                if str(date) not in coverage:
                    coverage[str(date)] = {}
                if key not in coverage[str(date)]:
                    coverage[str(date)][key] = 0.0
                coverage[str(date)][key] += float(ag_hours_per_workday)

    columns = {'x': []}
    for date in sorted(coverage.keys()):
        columns['x'].append(date)
        for proj, hours in coverage[date].items():
            if proj not in columns:
                columns[proj] = [0.0] * (len(columns['x']) - 1)
            columns[proj].append(hours)
        
        expected_len = len(columns['x'])
        for check_key, vals in columns.items():
            while len(vals) != expected_len:
                columns[check_key].append(0.0)

    c3_columns = []
    for proj, vals in columns.items():
        if proj != 'x':
            c3_columns.append([proj] + vals)
        else:
            c3_columns.insert(0, [proj] + vals)

    total_hours = 0.0
    total_utilization_hours = 0.0
    for user in Group.objects.get(id=1).user_set.filter(is_active=True):
        total_hours += user.profile.hours_per_week
        total_utilization_hours += user.profile.hours_per_week * user.profile.get_utilization

    c3_columns_by_week = []
    i = -1
    j = 1
    for date_str in c3_columns[0][1:]:
        i += 1
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        if i == 0:
            sun_date = date
            while sun_date.weekday() != 6:
                sun_date -= datetime.timedelta(days=1)
            c3_columns_by_week.append(['x', str(sun_date)])
            i += 1
            for cols in c3_columns[1:]:
                c3_columns_by_week.append([cols[0], cols[i]])
        else:
            index = 1
            
            last_sun_date = sun_date
            sun_date = date
            while sun_date.weekday() != 6:
                sun_date -= datetime.timedelta(days=1)

            new_week = last_sun_date != sun_date
            if new_week:
                j += 1
                c3_columns_by_week[0].append(str(sun_date))
            
            for cols in c3_columns[1:]:
                if new_week:
                    c3_columns_by_week[index].append(0.0)
                c3_columns_by_week[index][j] += c3_columns[index][i]
                index += 1

    # another reformat to get dictionary... again...
    future_data = {}
    future_dates = c3_columns_by_week[0][1:]
    for i, proj_act in enumerate(c3_columns_by_week[1:]):
        future_data[proj_act[0]] = {}
        for j, val in enumerate(proj_act[1:]):
            future_data[proj_act[0]][future_dates[j]] = val

    # get last ~3 months data
    start_time = datetime.datetime.now()
    start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    start_time -= datetime.timedelta(days=90)
    while start_time.weekday() != 6:
        start_time -= datetime.timedelta(days=1)

    past_data, past_dates, past_project_types, past_project_statuses, \
    past_clients, past_billable, past_chart_filters, past_export_filters = \
    get_company_summary_by_week(activity_goalQ, start_time, datetime.datetime.now())

    chart_filters.update(past_chart_filters)
    export_filters.update(past_export_filters)

    project_statuses = [{'id':ps.id, 'label':ps.label} for ps in list(set(project_statuses + past_project_statuses))]
    # project_types = sorted([{'id':pt.id, 'label':pt.label} for pt in list(set(project_types))], lambda pt:pt.label)
    project_types = [{'id':pt.id, 'label':pt.label} for pt in list(set(project_types + past_project_types))]
    # clients = sorted([{'id':c.id, 'label':c.name} for c in list(set(clients))], lambda c:c.name)
    clients = [{'id':c.id, 'label':c.name} for c in list(set(clients + past_clients))]
    
    billable = list(set(billable + past_billable))
    if len(billable) == 2:
        billable = [{'id': 'true', 'label': 'Billable'}, {'id': 'false', 'label':'Non-billable'}]
    elif len(billable) == 0:
        billable = []
    elif billable[0] == True:
        billable = [{'id': 'true', 'label': 'Billable'}]
    elif billable[0] == False:
        billable = [{'id': 'false', 'label':'Non-billable'}]

    # combine past and future
    all_data = past_data
    for proj_act, hours in future_data.items():
        if proj_act in all_data:
            for week, hour in hours.items():
                if week in all_data[proj_act]:
                    all_data[proj_act][week] += Decimal(hour)
                else:
                    all_data[proj_act][week] = Decimal(hour)
        else:
            all_data[proj_act] = hours

    # combine into c3 data structure
    c3_columns_by_week_with_past = []
    dates = sorted(list(set(past_dates + future_dates)))
    dates_col = ['x'] + dates
    c3_columns_by_week_with_past.append(dates_col)
    for proj_act, hours in all_data.items():
        col = [proj_act]
        for week in dates:
            if week in hours:
                col.append(float(hours[week]))
            else:
                col.append(0.0)
        c3_columns_by_week_with_past.append(col)

    total_avg = ['Total Avg Hours']
    util_avg = ['Utilization Avg Hours']
    for i in range(1, len(c3_columns_by_week)):
        total_avg.append(total_hours)
        util_avg.append(total_utilization_hours)
    c3_columns_by_week_with_past.append(total_avg)
    c3_columns_by_week_with_past.append(util_avg)

    keys = all_data.keys()
    # keys.remove('x')
    data = {'columns': c3_columns_by_week_with_past,
            'keys': keys,
            'avg_hours': float(hours_per_week / Decimal('5.0')),
            'filters': {'chart_filters': chart_filters,
                        'project_statuses': project_statuses,
                        'project_types': project_types,
                        'clients': clients,
                        'billable': billable}}
    return data, export_filters

def get_company_summary_by_week(entryQ, start_time, end_time):
    data = {}
    chart_filters = {}
    export_filters = {}
    project_types = []
    project_statuses = []
    clients = []
    billable = []
    dates = []
    for entry in Entry.objects.filter(entryQ, start_time__gte=start_time,
        end_time__lte=end_time):

        key = '%s - %s' % (entry.project.code, entry.activity.name)
        if key not in data:
            data[key] = {}
            
            project_types.append(entry.project.type)
            project_statuses.append(entry.project.status)
            clients.append(entry.project.business)
            billable.append(entry.project.type.billable and entry.activity.billable)
            chart_filters[key] = {
                'project-type': entry.project.type.id,
                'project-status': entry.project.status.id,
                'billable': entry.project.type.billable and entry.activity.billable,
                'client': entry.project.business.id}
            export_filters[key] = {
                'project-type': entry.project.type,
                'project-status': entry.project.status,
                'billable': entry.project.type.billable and entry.activity.billable,
                'client': entry.project.business,
                'activity': entry.activity,
                'project': entry.project}

        date = entry.start_time.date()
        while date.weekday() != 6:
            date -= datetime.timedelta(days=1)
        if str(date) not in data[key]:
            data[key][str(date)] = Decimal('0.0')
            dates.append(str(date))
        data[key][str(date)] += entry.hours

    return data, dates, project_types, project_statuses, \
        clients, billable, chart_filters, export_filters
