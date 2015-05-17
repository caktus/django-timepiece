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

from timepiece.crm.models import ActivityGoal, PaidTimeOffRequest

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


def generate_dates(start=None, end=None, by='week'):
    if start:
        start = add_timezone(start)
    if end:
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
                   total_column=False, by='user', writedown=None):
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
            dates.append(find_overtime(dates))
        dates = [date or '' for date in dates]
        rows.append((name, thing_id, dates))
    if total_column:
        totals.append(sum(totals))
    totals = [total or '' for total in totals]
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

def get_company_backlog_chart_data():
    """
    Creates the data objects required by the c3 frond-end visualization
    """

    def new_empty_date():
        # return {'Holiday': 0.0,
        #         'Approved Time Off': 0.0}
        return {}

    employees = Group.objects.get(id=1).user_set.filter(is_active=True).order_by('last_name', 'first_name')
    hours_per_week = Decimal('0.0')
    for employee in employees:
        print 'hours', employee.profile.hours_per_week, hours_per_week
        hours_per_week += Decimal(employee.profile.hours_per_week)
    
    coverage = {}

    # start_week = get_week_start(datetime.date.today()).date()
    start_week = datetime.date.today()
    activity_goals = ActivityGoal.objects.filter(
        employee__in=employees, end_date__gte=start_week, 
        project__status=get_setting(
            'TIMEPIECE_DEFAULT_PROJECT_STATUS'))

    if activity_goals.count() == 0:
         return {}

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

    # determine holidays and add time (whether paid or not)
    holidays = [h['date'] for h in Holiday.holidays_between_dates(
        start_week, end_week, {'paid_holiday': True})]
    for holiday in holidays:
        if str(holiday) not in coverage:
            coverage[str(holiday)] = new_empty_date()
        coverage[str(holiday)]['Holiday'] = float(hours_per_week / Decimal('5.0'))

    # add Time Off requests as holidays
    # TODO: should make this smarter so that if it is a partial day it
    #       does not count as a full day
    userprofiles = [employee.profile for employee in employees]
    for ptor in PaidTimeOffRequest.objects.filter(
        Q(user_profile__in=userprofiles),
        Q(pto_start_date__gte=start_week)|Q(pto_end_date__gte=end_week),
        Q(status='approved')|Q(status='processed')):
    # for ptor in employee.profile.paidtimeoffrequest_set.filter(
    #     Q(pto_start_date__gte=start_week)|Q(pto_end_date__gte=end_week),
    #     Q(status='approved')|Q(status='processed')):
        
        num_workdays = max(workdays.networkdays(ptor.pto_start_date, 
            ptor.pto_end_date, holidays), 1)
        ptor_hours_per_day = ptor.amount / Decimal(num_workdays)

        for i in range((ptor.pto_end_date-ptor.pto_start_date).days + 1):
            date = ptor.pto_start_date + datetime.timedelta(days=i)
            if date.weekday() < 5:
                holidays.append(date)
                if str(date) not in coverage:
                    coverage[str(date)] = \
                        new_empty_date()
                coverage[str(date)]['Approved Time Off'] = \
                    float(ptor_hours_per_day)

    y_axes = {'Holiday': ['data1'],
              'Approved Time Off': ['data2']}
    data_counter = 3
    for activity_goal in activity_goals:
        if activity_goal.project.code not in y_axes.keys():
            y_axes[activity_goal.project.code] = ['data%s'%data_counter]
            data_counter += 1

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
                    coverage[str(date)] = new_empty_date()
                if activity_goal.project.code not in coverage[str(date)]:
                    coverage[str(date)][activity_goal.project.code] = 0.0
                coverage[str(date)][activity_goal.project.code] += \
                    float(ag_hours_per_workday)

    # x_axis = ['x']

    # for i in range((end_week - start_week).days + 1):
    #     date = start_week + datetime.timedelta(days=i)
    #     x_axis.append(str(date))
        
    #     for project in y_axes.keys():
    #         pass

    # sorted_coverage = []
    # for k in sorted(coverage.keys()):
    #     sorted_coverage = coverage[k]
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
    schedule = ['Avg Hours']
    week_dict = employee.profile.week_dict()
    for date_str in sorted(coverage.keys()):
        date = datetime.datetime.strptime(date_str, '%Y-%m-%d', ).date()
        schedule.append(float(hours_per_week / Decimal('5.0')))
    
    # c3_columns.append(['Regular Schedule'] + [float(avg_hours_per_day)]*len(columns['x']))
    c3_columns.append(schedule)
    keys = columns.keys()
    keys.remove('x')
    data = {'columns': c3_columns,
            'keys': keys,
            'avg_hours': float(hours_per_week / Decimal('5.0'))}
    return data