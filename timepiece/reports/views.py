import csv
import json

from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from itertools import groupby

from django.contrib.auth.decorators import permission_required
from django.db.models import Sum, Q, Min, Max
from django.http import HttpResponse
from django.shortcuts import render
from django.template.defaultfilters import date as date_format_filter
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from timepiece import utils
from timepiece.utils.csv import CSVViewMixin, DecimalEncoder

from timepiece.contracts.models import ProjectContract
from timepiece.entries.models import Entry, ProjectHours
from timepiece.reports.forms import (
    BillableHoursReportForm, HourlyReportForm, ProductivityReportForm,
    PayrollSummaryReportForm)
from timepiece.reports.utils import (
    get_project_totals, get_payroll_totals, generate_dates, get_week_window)


class ReportMixin(object):
    """Common data for the Hourly & Billable Hours reports."""

    @method_decorator(permission_required('entries.view_entry_summary'))
    def dispatch(self, request, *args, **kwargs):
        return super(ReportMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Processes form data to get relevant entries & date_headers."""
        context = super(ReportMixin, self).get_context_data(**kwargs)

        form = self.get_form()
        if form.is_valid():
            data = form.cleaned_data
            start, end = form.save()
            entryQ = self.get_entry_query(start, end, data)
            trunc = data['trunc']
            if entryQ:
                vals = ('pk', 'activity', 'project', 'project__name',
                        'project__status', 'project__type__label')
                entries = Entry.objects.date_trunc(
                    trunc, extra_values=vals).filter(entryQ)
            else:
                entries = Entry.objects.none()

            end = end - relativedelta(days=1)
            date_headers = generate_dates(start, end, by=trunc)
            context.update({
                'from_date': start,
                'to_date': end,
                'date_headers': date_headers,
                'entries': entries,
                'filter_form': form,
                'trunc': trunc,
            })
        else:
            context.update({
                'from_date': None,
                'to_date': None,
                'date_headers': [],
                'entries': Entry.objects.none(),
                'filter_form': form,
                'trunc': '',
            })

        return context

    def get_entry_query(self, start, end, data):
        """Builds Entry query from form data."""
        # Entry types.
        incl_billable = data.get('billable', True)
        incl_nonbillable = data.get('non_billable', True)
        incl_leave = data.get('paid_leave', True)

        # If no types are selected, shortcut & return nothing.
        if not any((incl_billable, incl_nonbillable, incl_leave)):
            return None

        # All entries must meet time period requirements.
        basicQ = Q(end_time__gte=start, end_time__lt=end)

        # Filter by project for HourlyReport.
        projects = data.get('projects', None)
        basicQ &= Q(project__in=projects) if projects else Q()

        # Filter by user, activity, and project type for BillableReport.
        if 'users' in data:
            basicQ &= Q(user__in=data.get('users'))
        if 'activities' in data:
            basicQ &= Q(activity__in=data.get('activities'))
        if 'project_types' in data:
            basicQ &= Q(project__type__in=data.get('project_types'))

        # If all types are selected, no further filtering is required.
        if all((incl_billable, incl_nonbillable, incl_leave)):
            return basicQ

        # Filter by whether a project is billable or non-billable.
        billableQ = None
        if incl_billable and not incl_nonbillable:
            billableQ = Q(activity__billable=True, project__type__billable=True)
        if incl_nonbillable and not incl_billable:
            billableQ = Q(activity__billable=False) | Q(project__type__billable=False)

        # Filter by whether the entry is paid leave.
        leave_ids = utils.get_setting('TIMEPIECE_PAID_LEAVE_PROJECTS').values()
        leaveQ = Q(project__in=leave_ids)
        if incl_leave:
            extraQ = (leaveQ | billableQ) if billableQ else leaveQ
        else:
            extraQ = (~leaveQ & billableQ) if billableQ else ~leaveQ

        return basicQ & extraQ

    def get_headers(self, date_headers, from_date, to_date, trunc):
        """Adjust date headers & get range headers."""
        date_headers = list(date_headers)

        # Earliest date should be no earlier than from_date.
        if date_headers and date_headers[0] < from_date:
            date_headers[0] = from_date

        # When organizing by week or month, create a list of the range for
        # each date header.
        if date_headers and trunc != 'day':
            count = len(date_headers)
            range_headers = [0] * count
            for i in range(count - 1):
                range_headers[i] = (
                    date_headers[i], date_headers[i + 1] - relativedelta(days=1))
            range_headers[count - 1] = (date_headers[count - 1], to_date)
        else:
            range_headers = date_headers
        return date_headers, range_headers

    def get_previous_month(self):
        """Returns date range for the previous full month."""
        end = utils.get_month_start() - relativedelta(days=1)
        end = utils.to_datetime(end)
        start = utils.get_month_start(end)
        return start, end


class HourlyReport(ReportMixin, CSVViewMixin, TemplateView):
    template_name = 'timepiece/reports/hourly.html'

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file."""
        content = []
        date_headers = context['date_headers']

        headers = ['Name']
        headers.extend([date.strftime('%m/%d/%Y') for date in date_headers])
        headers.append('Total')
        content.append(headers)

        summaries = context['summaries']

        summary = summaries.get(self.export, [])

        for rows, totals in summary:
            for name, user_id, hours in rows:
                data = [name]
                data.extend(hours)
                content.append(data)
            total = ['Totals']
            total.extend(totals)
            content.append(total)
        return content

    @property
    def defaults(self):
        """Default filter form data when no GET data is provided."""
        # Set default date span to previous week.
        (start, end) = get_week_window(timezone.now() - relativedelta(days=7))
        return {
            'from_date': start,
            'to_date': end,
            'billable': True,
            'non_billable': False,
            'paid_leave': False,
            'trunc': 'day',
            'projects': [],
        }

    def get(self, request, *args, **kwargs):
        self.export = request.GET.get('export', False)
        context = self.get_context_data()
        kls = CSVViewMixin if self.export else TemplateView
        return kls.render_to_response(self, context)

    def get_context_data(self, **kwargs):
        context = super(HourlyReport, self).get_context_data(**kwargs)

        # Sum the hours totals for each user & interval.
        entries = context['entries']
        date_headers = context['date_headers']

        summaries = []
        if context['entries']:
            summaries.append(('By User', get_project_totals(
                entries.order_by('user__last_name', 'user__id', 'date'),
                date_headers, 'total', total_column=True, by='user')))

            entries = entries.order_by('project__type__label', 'project__name',
                                       'project__id', 'date')
            func = lambda x: x['project__type__label']
            for label, group in groupby(entries, func):
                title = label + ' Projects'
                summaries.append((
                    title,
                    get_project_totals(
                        list(group),
                        date_headers,
                        'total',
                        total_column=True,
                        by='project',
                    ),
                ))

        # Adjust date headers & create range headers.
        from_date = context['from_date']
        from_date = utils.add_timezone(from_date) if from_date else None
        to_date = context['to_date']
        to_date = utils.add_timezone(to_date) if to_date else None
        trunc = context['trunc']
        date_headers, range_headers = self.get_headers(
            date_headers, from_date, to_date, trunc)

        context.update({
            'date_headers': date_headers,
            'summaries': OrderedDict(summaries),
            'range_headers': range_headers,
        })
        return context

    def get_filename(self, context):
        request = self.request.GET.copy()
        from_date = request.get('from_date')
        to_date = request.get('to_date')
        return 'hours_{0}_to_{1}_by_{2}.csv'.format(
            from_date, to_date, context.get('trunc', ''))

    def get_form(self):
        data = self.request.GET or self.defaults
        data = data.copy()  # make mutable
        # Fix booleans - the strings "0" and "false" are True in Python
        for key in ['billable', 'non_billable', 'paid_leave']:
            data[key] = key in data and str(data[key]).lower() in ('on', 'true', '1')
        return HourlyReportForm(data)


class BillableHours(ReportMixin, TemplateView):
    template_name = 'timepiece/reports/billable_hours.html'

    @property
    def defaults(self):
        """Default filter form data when no GET data is provided."""
        start, end = self.get_previous_month()
        return {
            'from_date': start,
            'to_date': end,
            'trunc': 'week',
        }

    def get_context_data(self, **kwargs):
        context = super(BillableHours, self).get_context_data(**kwargs)

        entries = context['entries']
        date_headers = context['date_headers']
        data_map = self.get_hours_data(entries, date_headers)

        from_date = context['from_date']
        to_date = context['to_date']
        trunc = context['trunc']
        kwargs = {trunc + 's': 1}  # For relativedelta

        keys = sorted(data_map.keys())
        data_list = [['Date', 'Billable', 'Non-billable']]
        for i in range(len(keys)):
            start = keys[i]
            start = start if start >= from_date else from_date
            end = start + relativedelta(**kwargs) - relativedelta(days=1)
            end = end if end <= to_date else to_date

            if start != end:
                label = ' - '.join([date_format_filter(d, 'M j') for d in (start, end)])
            else:
                label = date_format_filter(start, 'M j')
            billable = data_map[keys[i]]['billable']
            nonbillable = data_map[keys[i]]['nonbillable']
            data_list.append([label, billable, nonbillable])

        context.update({
            'data': json.dumps(data_list, cls=DecimalEncoder),
        })
        return context

    def get_form(self):
        if self.request.GET:
            return BillableHoursReportForm(self.request.GET)
        else:
            # Select all available users, activities, and project types.
            return BillableHoursReportForm(self.defaults, select_all=True)

    def get_hours_data(self, entries, date_headers):
        """Sum billable and non-billable hours across all users."""
        project_totals = get_project_totals(
            entries, date_headers, total_column=False) if entries else []

        data_map = {}
        for rows, totals in project_totals:
            for user, user_id, periods in rows:
                for period in periods:
                    day = period['day']
                    if day not in data_map:
                        data_map[day] = {'billable': 0, 'nonbillable': 0}
                    data_map[day]['billable'] += period['billable']
                    data_map[day]['nonbillable'] += period['nonbillable']

        return data_map


@permission_required('entries.view_payroll_summary')
def report_payroll_summary(request):
    date = timezone.now() - relativedelta(months=1)
    from_date = utils.get_month_start(date).date()
    to_date = from_date + relativedelta(months=1)

    year_month_form = PayrollSummaryReportForm(request.GET or None, initial={
        'month': from_date.month,
        'year': from_date.year,
    })

    if year_month_form.is_valid():
        from_date, to_date = year_month_form.save()
    last_billable = utils.get_last_billable_day(from_date)
    projects = utils.get_setting('TIMEPIECE_PAID_LEAVE_PROJECTS')
    weekQ = Q(end_time__gt=utils.get_week_start(from_date),
              end_time__lt=last_billable + relativedelta(days=1))
    monthQ = Q(end_time__gt=from_date, end_time__lt=to_date)
    workQ = ~Q(project__in=projects.values())
    statusQ = Q(status=Entry.INVOICED) | Q(status=Entry.APPROVED)
    # Weekly totals
    week_entries = Entry.objects.date_trunc('week').filter(
        weekQ, statusQ, workQ
    )
    date_headers = generate_dates(from_date, last_billable, by='week')
    weekly_totals = list(get_project_totals(week_entries, date_headers,
                                            'total', overtime=True))
    # Monthly totals
    leave = Entry.objects.filter(monthQ, ~workQ)
    leave = leave.values('user', 'hours', 'project__name')
    extra_values = ('project__type__label',)
    month_entries = Entry.objects.date_trunc('month', extra_values)
    month_entries_valid = month_entries.filter(monthQ, statusQ, workQ)
    labels, monthly_totals = get_payroll_totals(month_entries_valid, leave)
    # Unapproved and unverified hours
    entries = Entry.objects.filter(monthQ).order_by()  # No ordering
    user_values = ['user__pk', 'user__first_name', 'user__last_name']
    unverified = entries.filter(status=Entry.UNVERIFIED, user__is_active=True) \
                        .values_list(*user_values).distinct()
    unapproved = entries.filter(status=Entry.VERIFIED) \
                        .values_list(*user_values).distinct()
    return render(request, 'timepiece/reports/payroll_summary.html', {
        'from_date': from_date,
        'year_month_form': year_month_form,
        'date_headers': date_headers,
        'weekly_totals': weekly_totals,
        'monthly_totals': monthly_totals,
        'unverified': unverified,
        'unapproved': unapproved,
        'labels': labels,
    })


@permission_required('entries.view_entry_summary')
def report_productivity(request):
    report = []
    organize_by = None

    form = ProductivityReportForm(request.GET or None)
    if form.is_valid():
        project = form.cleaned_data['project']
        organize_by = form.cleaned_data['organize_by']
        export = request.GET.get('export', False)

        actualsQ = Q(project=project, end_time__isnull=False)
        actuals = Entry.objects.filter(actualsQ)
        projections = ProjectHours.objects.filter(project=project)
        entry_count = actuals.count() + projections.count()

        if organize_by == 'week' and entry_count > 0:
            # Determine the project's time range.
            amin, amax, pmin, pmax = (None, None, None, None)
            if actuals.count() > 0:
                amin = list(actuals.aggregate(Min('start_time')).values())[0]
                amin = utils.get_week_start(amin).date()
                amax = list(actuals.aggregate(Max('start_time')).values())[0]
                amax = utils.get_week_start(amax).date()
            if projections.count() > 0:
                pmin = list(projections.aggregate(Min('week_start')).values())[0]
                pmax = list(projections.aggregate(Max('week_start')).values())[0]
            current = min(amin, pmin) if (amin and pmin) else (amin or pmin)
            latest = max(amax, pmax) if (amax and pmax) else (amax or pmax)

            # Report for each week during the project's time range.
            while current <= latest:
                next_week = current + relativedelta(days=7)
                actual_hours = actuals.filter(start_time__gte=current, start_time__lt=next_week)
                actual_hours = list(actual_hours.aggregate(Sum('hours')).values())[0]
                projected_hours = projections.filter(
                    week_start__gte=current, week_start__lt=next_week)
                projected_hours = list(projected_hours.aggregate(Sum('hours')).values())[0]
                report.append([date_format_filter(current, 'M j, Y'),
                              actual_hours or 0, projected_hours or 0])
                current = next_week

        elif organize_by == 'user' and entry_count > 0:
            # Determine all users who worked on or were assigned to the
            # project.
            vals = ('user', 'user__first_name', 'user__last_name')
            ausers = list(actuals.values_list(*vals).distinct())
            pusers = list(projections.values_list(*vals).distinct())
            key = lambda x: (x[1] + x[2]).lower()  # Sort by name
            users = sorted(list(set(ausers + pusers)), key=key)

            # Report for each user.
            for user in users:
                name = '{0} {1}'.format(user[1], user[2])
                actual_hours = actuals.filter(user=user[0])
                actual_hours = list(actual_hours.aggregate(Sum('hours')).values())[0]
                projected_hours = projections.filter(user=user[0])
                projected_hours = list(projected_hours.aggregate(Sum('hours')).values())[0]
                report.append([name, actual_hours or 0, projected_hours or 0])

        col_headers = [organize_by.title(), 'Worked Hours', 'Assigned Hours']
        report.insert(0, col_headers)

        if export:
            response = HttpResponse(content_type='text/csv')
            filename = '{0}_productivity'.format(project.name)
            content_disp = 'attachment; filename={0}.csv'.format(filename)
            response['Content-Disposition'] = content_disp
            writer = csv.writer(response)
            for row in report:
                writer.writerow(row)
            return response

    return render(request, 'timepiece/reports/productivity.html', {
        'form': form,
        'report': json.dumps(report, cls=DecimalEncoder),
        'type': organize_by or '',
        'total_worked': sum([r[1] for r in report[1:]]),
        'total_assigned': sum([r[2] for r in report[1:]]),
    })


@permission_required('contracts.view_estimation_accuracy')
def report_estimation_accuracy(request):
    """
    Idea from Software Estimation, Demystifying the Black Art, McConnel 2006 Fig 3-3.
    """
    contracts = ProjectContract.objects.filter(
        status=ProjectContract.STATUS_COMPLETE,
        type=ProjectContract.PROJECT_FIXED
    )
    data = [('Target (hrs)', 'Actual (hrs)', 'Point Label')]
    for c in contracts:
        if c.contracted_hours() == 0:
            continue
        pt_label = "%s (%.2f%%)" % (c.name,
                                    c.hours_worked / c.contracted_hours() * 100)
        data.append((c.contracted_hours(), c.hours_worked, pt_label))
        chart_max = max([max(x[0], x[1]) for x in data[1:]])  # max of all targets & actuals
    return render(request, 'timepiece/reports/estimation_accuracy.html', {
        'data': json.dumps(data, cls=DecimalEncoder),
        'chart_max': chart_max,
    })
