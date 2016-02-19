import datetime
from dateutil.relativedelta import relativedelta

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db import transaction, DatabaseError
from django.db.models import Sum, Q
from django.db.models.expressions import F, Func, Value
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView

from timepiece import utils
from timepiece.templatetags.timepiece_tags import seconds_to_hours
from timepiece.utils.csv import CSVViewMixin
from timepiece.utils.search import SearchListView
from timepiece.utils.views import cbv_decorator

from timepiece.contracts.forms import InvoiceForm, OutstandingHoursFilterForm
from timepiece.contracts.models import ProjectContract, HourGroup, EntryGroup
from timepiece.entries.models import Project, Entry


@cbv_decorator(permission_required('contracts.add_projectcontract'))
class ContractDetail(DetailView):
    template_name = 'timepiece/contract/view.html'
    model = ProjectContract
    context_object_name = 'contract'
    pk_url_kwarg = 'contract_id'

    def get_context_data(self, *args, **kwargs):
        if 'today' not in kwargs:
            kwargs['today'] = datetime.date.today()
        if 'warning_date' not in kwargs:
            kwargs['warning_date'] = datetime.date.today() + relativedelta(weeks=2)
        return super(ContractDetail, self).get_context_data(*args, **kwargs)


@cbv_decorator(permission_required('contracts.add_projectcontract'))
class ContractList(ListView):
    template_name = 'timepiece/contract/list.html'
    model = ProjectContract
    context_object_name = 'contracts'
    queryset = ProjectContract.objects.filter(
        status=ProjectContract.STATUS_CURRENT).order_by('name')

    def get_context_data(self, *args, **kwargs):
        if 'today' not in kwargs:
            kwargs['today'] = datetime.date.today()
        if 'warning_date' not in kwargs:
            kwargs['warning_date'] = datetime.date.today() + relativedelta(weeks=2)
        kwargs['max_work_fraction'] = max(
            [0.0] + [c.fraction_hours for c in self.queryset.all()])
        kwargs['max_schedule_fraction'] = max(
            [0.0] + [c.fraction_schedule for c in self.queryset.all()])
        kwargs['projects_pending'] = ProjectContract.objects.filter(
            status=ProjectContract.STATUS_UPCOMING).order_by('name')
        kwargs['projects_complete'] = ProjectContract.objects.filter(
            status=ProjectContract.STATUS_COMPLETE).order_by('name')
        return super(ContractList, self).get_context_data(*args, **kwargs)


@login_required
@transaction.atomic
def create_invoice(request):
    pk = request.GET.get('project', None)
    to_date = request.GET.get('to_date', None)
    if not (pk and to_date):
        raise Http404
    from_date = request.GET.get('from_date', None)
    if not request.user.has_perm('crm.generate_project_invoice'):
        return HttpResponseForbidden('Forbidden')
    try:
        to_date = utils.add_timezone(
            datetime.datetime.strptime(to_date, '%Y-%m-%d'))
        if from_date:
            from_date = utils.add_timezone(
                datetime.datetime.strptime(from_date, '%Y-%m-%d'))
    except (ValueError, OverflowError):
        raise Http404
    project = get_object_or_404(Project, pk=pk)
    initial = {
        'project': project,
        'user': request.user,
        'from_date': from_date,
        'to_date': to_date,
    }
    entries_query = {
        'status': Entry.APPROVED,
        'end_time__lt': to_date + relativedelta(days=1),
        'project__id': project.id
    }
    if from_date:
        entries_query.update({'end_time__gte': from_date})
    invoice_form = InvoiceForm(request.POST or None, initial=initial)
    if request.POST and invoice_form.is_valid():
        entries = Entry.no_join.filter(**entries_query)
        if entries.exists():
            # LOCK the entries until our transaction completes - nobody
            # else will be able to lock or change them - see
            # https://docs.djangoproject.com/en/1.4/ref/models/querysets/#select-for-update
            # (This feature requires Django 1.4.)
            # If more than one request is trying to create an invoice from
            # these same entries, then the second one to get to this line will
            # throw a DatabaseError.  That can happen if someone double-clicks
            # the Create Invoice button.
            try:
                entries.select_for_update(nowait=True)
            except DatabaseError:
                # Whoops, we lost the race
                messages.add_message(request, messages.ERROR,
                                     "Lock error trying to get entries")
            else:
                # We got the lock, we can carry on
                invoice = invoice_form.save()
                Entry.no_join.filter(pk__in=entries).update(
                    status=invoice.status, entry_group=invoice)
                messages.add_message(request, messages.INFO,
                                     "Invoice created")
                return HttpResponseRedirect(reverse('view_invoice',
                                                    args=[invoice.pk]))
        else:
            messages.add_message(request, messages.ERROR,
                                 "No entries for invoice")
    else:
        entries = Entry.objects.filter(**entries_query)
        entries = entries.order_by('start_time')
        if not entries:
            raise Http404

    billable_entries = entries.filter(activity__billable=True) \
        .select_related()
    nonbillable_entries = entries.filter(activity__billable=False) \
        .select_related()
    return render(request, 'timepiece/invoice/create.html', {
        'invoice_form': invoice_form,
        'billable_entries': billable_entries,
        'nonbillable_entries': nonbillable_entries,
        'project': project,
        'billable_totals': HourGroup.objects.summaries(billable_entries),
        'nonbillable_totals': HourGroup.objects.summaries(nonbillable_entries),
        'from_date': from_date,
        'to_date': to_date,
    })


@permission_required('contracts.change_entrygroup')
def list_outstanding_invoices(request):
    form = OutstandingHoursFilterForm(request.GET or None)
    # Determine the query to make based on the form
    if form.is_valid() or not form.is_bound:
        form_data = form.get_form_data()
        # Adjust to_date so the query includes all of the last day
        to_date = form_data['to_date'] + relativedelta(days=1)
        from_date = form_data['from_date']
        statuses = form_data['statuses']
        dates = Q()
        dates &= Q(end_time__gte=from_date) if from_date else Q()
        dates &= Q(end_time__lt=to_date) if to_date else Q()
        billable = Q(project__type__billable=True, project__status__billable=True)
        entry_status = Q(status=Entry.APPROVED)
        project_status = Q(project__status__in=statuses) if statuses is not None else Q()
        # Calculate hours for each project
        ordering = ('project__type__label', 'project__status__label',
                    'project__business__name', 'project__name', 'status')
        project_totals = Entry.objects.filter(
            dates, billable, entry_status, project_status).order_by(*ordering)
        # Find users with unverified/unapproved entries to warn invoice creator
        date_range_entries = Entry.objects.filter(dates)
        user_values = ['user__pk', 'user__first_name', 'user__last_name']
        unverified = date_range_entries.filter(status=Entry.UNVERIFIED)
        unverified = unverified.values_list(*user_values).order_by('user__first_name').distinct()
        unapproved = date_range_entries.filter(status=Entry.VERIFIED)
        unapproved = unapproved.values_list(*user_values).order_by('user__first_name').distinct()
    else:
        project_totals = unverified = unapproved = Entry.objects.none()
    return render(request, 'timepiece/invoice/outstanding.html', {
        'date_form': form,
        'project_totals': project_totals,
        'unverified': unverified,
        'unapproved': unapproved,
        'to_date': form.get_to_date(),
        'from_date': form.get_from_date(),
    })


@cbv_decorator(permission_required('contracts.add_entrygroup'))
class ListInvoices(SearchListView):
    model = EntryGroup
    paginate_by = 20
    search_fields = ['user__username__icontains', 'project__name__icontains',
                     'comments__icontains', 'number__icontains']
    template_name = 'timepiece/invoice/list.html'

    def get_queryset(self):
        qs = super(ListInvoices, self).get_queryset()
        return qs.order_by('-end', '-id')


@cbv_decorator(permission_required('contracts.change_entrygroup'))
class InvoiceDetail(DetailView):
    template_name = 'timepiece/invoice/view.html'
    model = EntryGroup
    context_object_name = 'invoice'
    pk_url_kwarg = 'invoice_id'

    def get_context_data(self, **kwargs):
        context = super(InvoiceDetail, self).get_context_data(**kwargs)
        invoice = context['invoice']
        billable_entries = invoice.entries.filter(activity__billable=True)\
                                          .order_by('start_time')\
                                          .select_related()
        nonbillable_entries = invoice.entries.filter(activity__billable=False)\
                                             .order_by('start_time')\
                                             .select_related()
        return {
            'invoice': invoice,
            'billable_entries': billable_entries,
            'billable_totals': HourGroup.objects
                                        .summaries(billable_entries),
            'nonbillable_entries': nonbillable_entries,
            'nonbillable_totals': HourGroup.objects
                                           .summaries(nonbillable_entries),
            'from_date': invoice.start,
            'to_date': invoice.end,
            'project': invoice.project,
        }


class InvoiceEntriesDetail(InvoiceDetail):
    template_name = 'timepiece/invoice/view_entries.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceEntriesDetail, self).get_context_data(**kwargs)
        billable_entries = context['billable_entries']
        nonbillable_entries = context['nonbillable_entries']
        context.update({
            'billable_total': billable_entries.aggregate(hours=Sum(
                Func(F('hours'), Value(2), function='ROUND'))
            )['hours'],
            'nonbillable_total': nonbillable_entries.aggregate(hours=Sum(
                Func(F('hours'), Value(2), function='ROUND'))
            )['hours'],
        })
        return context


class InvoiceDetailCSV(CSVViewMixin, InvoiceDetail):

    def get_filename(self, context):
        invoice = context['invoice']
        project = str(invoice.project).replace(' ', '_')
        end_day = invoice.end.strftime('%m-%d-%Y')
        return 'Invoice-{0}-{1}'.format(project, end_day)

    def convert_context_to_csv(self, context):
        rows = []
        rows.append([
            'Date',
            'Weekday',
            'Name',
            'Location',
            'Time In',
            'Time Out',
            'Breaks',
            'Hours',
        ])
        for entry in context['billable_entries']:
            data = [
                entry.start_time.strftime('%x'),
                entry.start_time.strftime('%A'),
                entry.user.get_name_or_username(),
                entry.location,
                entry.start_time.strftime('%X'),
                entry.end_time.strftime('%X'),
                seconds_to_hours(entry.seconds_paused),
                "{0:.2f}".format(entry.hours),
            ]
            rows.append(data)
        total = context['billable_entries'].aggregate(hours=Sum(
            Func(F('hours'), Value(2), function='ROUND'))
        )['hours']
        rows.append(('', '', '', '', '', '', 'Total:', "{0:.2f}".format(total)))
        return rows


class InvoiceEdit(InvoiceDetail):
    template_name = 'timepiece/invoice/edit.html'

    def get_context_data(self, **kwargs):
        context = super(InvoiceEdit, self).get_context_data(**kwargs)
        invoice_form = InvoiceForm(instance=self.object)
        context.update({
            'invoice_form': invoice_form,
        })
        return context

    def post(self, request, **kwargs):
        pk = kwargs.get(self.pk_url_kwarg)
        invoice = get_object_or_404(EntryGroup, pk=pk)
        self.object = invoice
        initial = {
            'project': invoice.project,
            'user': request.user,
            'from_date': invoice.start,
            'to_date': invoice.end,
        }
        invoice_form = InvoiceForm(request.POST,
                                   initial=initial,
                                   instance=invoice)
        if invoice_form.is_valid():
            invoice_form.save()
            return HttpResponseRedirect(reverse('view_invoice', kwargs=kwargs))
        else:
            context = super(InvoiceEdit, self).get_context_data(**kwargs)
            context.update({
                'invoice_form': invoice_form,
            })
            return self.render_to_response(context)


class InvoiceDelete(InvoiceDetail):
    template_name = 'timepiece/invoice/delete.html'

    def post(self, request, **kwargs):
        pk = kwargs.get(self.pk_url_kwarg)
        invoice = get_object_or_404(EntryGroup, pk=pk)
        if 'delete' in request.POST:
            invoice.delete()
            return HttpResponseRedirect(reverse('list_invoices'))
        else:
            return redirect(reverse('edit_invoice', kwargs=kwargs))


@permission_required('contracts.change_entrygroup')
def delete_invoice_entry(request, invoice_id, entry_id):
    invoice = get_object_or_404(EntryGroup, pk=invoice_id)
    entry = get_object_or_404(Entry, pk=entry_id)
    if request.POST:
        entry.status = Entry.APPROVED
        entry.entry_group = None
        entry.save()
        url = reverse('edit_invoice', args=(invoice_id,))
        return HttpResponseRedirect(url)
    return render(request, 'timepiece/invoice/delete_entry.html', {
        'invoice': invoice,
        'entry': entry,
    })
