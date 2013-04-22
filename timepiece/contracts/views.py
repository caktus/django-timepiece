import datetime
from dateutil.relativedelta import relativedelta

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponse, HttpResponseRedirect, Http404,\
        HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView

from timepiece import utils
from timepiece.forms import DATE_FORM_FORMAT, DateForm, SearchForm
from timepiece.models import Project, Entry
from timepiece.templatetags.timepiece_tags import seconds_to_hours
from timepiece.views import CSVMixin

from timepiece.contracts.forms import InvoiceForm
from timepiece.contracts.models import ProjectContract, HourGroup, EntryGroup


class ContractDetail(DetailView):
    template_name = 'timepiece/contract/view.html'
    model = ProjectContract
    context_object_name = 'contract'
    pk_url_kwarg = 'contract_id'

    @method_decorator(permission_required('contracts.add_projectcontract'))
    def dispatch(self, *args, **kwargs):
        return super(ContractDetail, self).dispatch(*args, **kwargs)


class ContractList(ListView):
    template_name = 'timepiece/contract/list.html'
    model = ProjectContract
    context_object_name = 'contracts'
    queryset = ProjectContract.objects.filter(status='current')\
            .order_by('name')

    @method_decorator(permission_required('contracts.add_projectcontract'))
    def dispatch(self, *args, **kwargs):
        return super(ContractList, self).dispatch(*args, **kwargs)


@login_required
@transaction.commit_on_success
def create_invoice(request):
    pk = request.GET.get('project', None)
    to_date = request.GET.get('to_date', None)
    if not (pk and to_date):
        raise Http404
    from_date = request.GET.get('from_date', None)
    if not request.user.has_perm('timepiece.generate_project_invoice'):
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
        'status': 'approved',
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
                entries.update(status=invoice.status,
                               entry_group=invoice)
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
        'billable_totals': HourGroup.objects
            .summaries(billable_entries),
        'nonbillable_totals': HourGroup.objects
            .summaries(nonbillable_entries),
        'from_date': from_date,
        'to_date': to_date,
    })


@permission_required('contracts.change_entrygroup')
def list_outstanding_invoices(request):
    from_date = None
    to_date = utils.get_month_start().date()
    defaults = {
        'to_date': (to_date - relativedelta(days=1)).strftime(DATE_FORM_FORMAT),
    }
    date_form = DateForm(request.GET or defaults)
    if request.GET and date_form.is_valid():
        from_date, to_date = date_form.save()

    datesQ = Q()
    datesQ &= Q(end_time__gte=from_date) if from_date else Q()
    datesQ &= Q(end_time__lt=to_date) if to_date else Q()
    billableQ = Q(project__type__billable=True, project__status__billable=True)
    statusQ = Q(status='approved')
    ordering = ('project__type__label', 'project__status__label',
            'project__business__name', 'project__name', 'status')

    entries = Entry.objects.filter(datesQ, billableQ, statusQ)
    project_totals = entries.order_by(*ordering)

    return render(request, 'timepiece/invoice/outstanding.html', {
        'date_form': date_form,
        'project_totals': project_totals if to_date else [],
        'to_date': to_date - relativedelta(days=1) if to_date else '',
        'from_date': from_date,
    })


@permission_required('contracts.add_entrygroup')
def list_invoices(request):
    search_form = SearchForm(request.GET)
    query = Q()
    if search_form.is_valid():
        search = search_form.save()
        query |= Q(user__username__icontains=search)
        query |= Q(project__name__icontains=search)
        query |= Q(comments__icontains=search)
        query |= Q(number__icontains=search)
    invoices = EntryGroup.objects.filter(query).order_by('-created')
    return render(request, 'timepiece/invoice/list.html', {
        'invoices': invoices,
        'search_form': search_form,
    })


class InvoiceDetail(DetailView):
    template_name = 'timepiece/invoice/view.html'
    model = EntryGroup
    context_object_name = 'invoice'
    pk_url_kwarg = 'invoice_id'

    @method_decorator(permission_required('contracts.change_entrygroup'))
    def dispatch(self, *args, **kwargs):
        return super(InvoiceDetail, self).dispatch(*args, **kwargs)

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
            'billable_totals': HourGroup.objects\
                                        .summaries(billable_entries),
            'nonbillable_entries': nonbillable_entries,
            'nonbillable_totals': HourGroup.objects\
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
            'billable_total': billable_entries \
                              .aggregate(hours=Sum('hours'))['hours'],
            'nonbillable_total': nonbillable_entries\
                                 .aggregate(hours=Sum('hours'))['hours'],
        })
        return context


class InvoiceDetailCSV(CSVMixin, InvoiceDetail):

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
                entry.hours,
            ]
            rows.append(data)
        total = context['billable_entries'].aggregate(hours=Sum('hours'))['hours']
        rows.append(('', '', '', '', '', '', 'Total:', total))
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
        entry.status = 'approved'
        entry.entry_group = None
        entry.save()
        url = reverse('edit_invoice', args=(invoice_id,))
        return HttpResponseRedirect(url)
    return render(request, 'timepiece/invoice/delete_entry.html', {
        'invoice': invoice,
        'entry': entry,
    })


