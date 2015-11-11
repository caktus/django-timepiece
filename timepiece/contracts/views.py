import datetime
from dateutil.relativedelta import relativedelta
import json
import math

import os.path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics, ttfonts
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Frame, Table, TableStyle
from reportlab.lib import colors

from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import transaction, DatabaseError
from django.db.models import Sum, Q
from django.forms import widgets
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import (ListView, DetailView, CreateView,
    UpdateView, DeleteView, View)

from django.contrib.staticfiles.templatetags.staticfiles import static

from django.utils import formats

from timepiece import utils
from timepiece.crm.models import Business
from timepiece.templatetags.timepiece_tags import seconds_to_hours
from timepiece.utils.csv import CSVViewMixin
from timepiece.utils.search import SearchListView
from timepiece.utils.views import cbv_decorator

from timepiece.contracts.forms import (InvoiceForm,
    OutstandingHoursFilterForm, CreateEditContractRateForm,
    CreateEditContractForm, CreateEditContractBudgetForm,
    CreateEditContractHourForm, ContractSearchForm,
    AddContractNoteForm)
from timepiece.contracts.models import (ProjectContract, HourGroup,
    EntryGroup, ContractRate, ProjectContract, ContractAttachment,
    ContractBudget, ContractHour, ContractNote)
from timepiece.entries.models import Project, Entry, Activity

from ajaxuploader.views import AjaxFileUploader
from ajaxuploader.backends.mongodb import MongoDBUploadBackend

try:
    from workflow.general_task.forms import SelectGeneralTaskForm
    from workflow.models import GeneralTask
except:
    pass

@cbv_decorator(permission_required('contracts.add_projectcontract'))
class CreateContract(CreateView):
    model = ProjectContract
    form_class = CreateEditContractForm
    template_name = 'timepiece/contract/create_edit.html'

@cbv_decorator(permission_required('contracts.change_projectcontract'))
class EditContract(UpdateView):
    model = ProjectContract
    form_class = CreateEditContractForm
    template_name = 'timepiece/contract/create_edit.html'
    pk_url_kwarg = 'contract_id'

@cbv_decorator(permission_required('contracts.delete_projectcontract'))
class DeleteContract(DeleteView):
    model = ProjectContract
    success_url = reverse_lazy('list_contracts')
    pk_url_kwarg = 'contract_id'
    template_name = 'timepiece/delete_object.html'

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
        context = super(ContractDetail, self).get_context_data(*args, **kwargs)
        context['add_contract_note_form'] = AddContractNoteForm()

        try:
            context['add_general_task_form'] = SelectGeneralTaskForm()
        except:
            pass

        return context


@cbv_decorator(permission_required('contracts.add_projectcontract'))
class ContractList(SearchListView, CSVViewMixin):
    model = ProjectContract
    form_class = ContractSearchForm
    redirect_if_one_result = True
    search_fields = ['name__icontains']
    context_object_name = 'contracts'
    template_name = 'timepiece/contract/list.html'

    def get(self, request, *args, **kwargs):
        if len(request.GET.keys()) == 0:
            return HttpResponseRedirect(reverse('list_contracts') \
                + '?status=' + ProjectContract.STATUS_CURRENT)
        self.export_contract_list = request.GET.get(
            'export_contract_list', False)
        if self.export_contract_list:
            kls = CSVViewMixin

            form_class = self.get_form_class()
            self.form = self.get_form(form_class)
            self.object_list = self.get_queryset()
            self.object_list = self.filter_results(self.form, self.object_list)

            # allow_empty = self.get_allow_empty()
            # if not allow_empty and len(self.object_list) == 0:
            #     raise Http404("No results found.")

            context = self.get_context_data(form=self.form,
                object_list=self.object_list)

            return kls.render_to_response(self, context)
        else:
            return super(ContractList, self).get(request, *args, **kwargs)

    def filter_form_valid(self, form, queryset):
        queryset = super(ContractList, self).filter_form_valid(form, queryset)
        status = form.cleaned_data['status']
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by('name')

    def get_filename(self, context):
        request = self.request.GET.copy()
        status = request.get('status', 'all') or 'all'
        search = request.get('search', '(empty)') or '(empty)'
        return 'contract_list_{0}_{1}_{2}'.format(
            datetime.datetime.now().strftime('%Y%m%d_%H%M%S'),
            status, search)

    def get_context_data(self, *args, **kwargs):
        if 'today' not in kwargs:
            kwargs['today'] = datetime.date.today()
        if 'warning_date' not in kwargs:
            kwargs['warning_date'] = datetime.date.today() + relativedelta(weeks=2)
        kwargs['max_work_fraction'] = max(
            [0.0] + [c.fraction_value for c in self.object_list])
        kwargs['max_schedule_fraction'] = max(
            [0.0] + [c.fraction_schedule for c in self.object_list])
        return super(ContractList, self).get_context_data(*args, **kwargs)

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file."""
        content = []
        contracts = context['contracts']
        if self.export_contract_list:
            headers = ['Contract Name', 'Start Date', 'End Date',
                       'Contract Value', 'Contract Value Unit',
                       'Billable Hours Works', 'Non-Billable Hours Worked',
                       'Schedule Progress', 'Ceiling Progress',
                       'Contract Type', 'Client Expense Category',
                       'Tags', 'Projects -->']
            content.append(headers)
            for contract in contracts:
                row = [contract.name, contract.start_date, contract.end_date,
                       contract.contract_value(),
                       contract.get_ceiling_type_display(),
                       contract.hours_worked,
                       contract.nonbillable_hours_worked,
                       contract.fraction_schedule, contract.fraction_value,
                       contract.get_type_display(),
                       contract.get_client_expense_category_display(),
                       ', '.join(
                        [t.name.strip() for t in contract.tags.all()])]
                for project in contract.projects.all():
                    row.append(str(project))
                content.append(row)
        return content

@cbv_decorator(permission_required('contracts.change_projectcontract'))
class AddContractGeneralTask(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=501)

    def post(self, request, *args, **kwargs):
        try:
            contract = ProjectContract.objects.get(id=int(kwargs['contract_id']))
            general_task = SelectGeneralTaskForm(request.POST).get_general_task()
            if general_task.contract is None:
                general_task.contract = contract
                general_task.save()
            else:
                msg = '%s already belongs to Contract <a href="' + \
                reverse('view_contract', args=(general_task.contract.id,)) + \
                '">%s.  Please remove it from that Contract before ' + \
                'associating with this one.' % (
                    general_task.form_id, general_task.contract.code)
                messages.error(request, msg)
        except:
            print sys.exc_info(), traceback.format_exc()
        finally:
            return HttpResponseRedirect(request.GET.get('next', None)
                or reverse_lazy('view_project', args=(contract.id,)))

@cbv_decorator(permission_required('contracts.change_projectcontract'))
class RemoveContractGeneralTask(View):

    def get(self, request, *args, **kwargs):
        try:
            contract = ProjectContract.objects.get(id=int(kwargs['contract_id']))
            general_task_id = request.GET.get('general_task_id')
            general_task = GeneralTask.objects.get(id=int(general_task_id))
            general_task.contract = None
            general_task.save()
        except:
            print sys.exc_info(), traceback.format_exc()
        finally:
            return HttpResponseRedirect(request.GET.get('next', None)
                or reverse_lazy('view_contract', args=(contract.id,)))

@permission_required('contracts.add_contractincrement')
def add_contract_increment(request, contract_id):
    contract = ProjectContract.objects.get(id=contract_id)
    if contract.ceiling_type == contract.HOURS:
        return HttpResponseRedirect(reverse('add_contract_hours', args=(contract.id,)))
    elif contract.ceiling_type == contract.BUDGET:
        return HttpResponseRedirect(reverse('add_contract_budget', args=(contract.id,)))
    else:
        return HttpResponseRedirect(reverse('dashboard'))

@cbv_decorator(permission_required('crm.change_projectcontract'))
class ContractTags(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=200)

    def post(self, request, *args, **kwargs):
        contract = ProjectContract.objects.get(id=int(kwargs['contract_id']))
        tag = request.POST.get('tag')
        for t in tag.split(','):
            if len(t):
                contract.tags.add(t)
        tags = [{'id': t.id,
                 'url': reverse('similar_items', args=(t.id,)),
                 'name':t.name} for t in contract.tags.all()]
        return HttpResponse(json.dumps({'tags': tags}),
                            content_type="application/json",
                            status=200)

@cbv_decorator(permission_required('crm.change_projectcontract'))
class RemoveContractTag(View):

    def get(self, request, *args, **kwargs):
        return HttpResponse(status=501)

    def post(self, request, *args, **kwargs):
        if request.user.is_superuser or \
            bool(len(request.user.groups.filter(id=8))):
            contract = ProjectContract.objects.get(
                id=int(kwargs['contract_id']))
            tag = request.POST.get('tag')
            if len(tag):
                contract.tags.remove(tag)
        tags = [{'id': t.id,
                 'url': reverse('similar_items', args=(t.id,)),
                 'name':t.name} for t in contract.tags.all()]
        return HttpResponse(json.dumps({'tags': tags}),
                            content_type="application/json",
                            status=200)

@cbv_decorator(permission_required('contracts.add_contractbudget'))
class AddContractBudget(CreateView):
    model = ContractBudget
    form_class = CreateEditContractBudgetForm
    template_name = 'timepiece/contract/hour/create_edit.html'

    def get_form(self, *args, **kwargs):
        form = super(AddContractBudget, self).get_form(*args, **kwargs)
        form.fields['contract'].widget = widgets.HiddenInput()
        contract = ProjectContract.objects.get(
            id=int(self.kwargs['contract_id']))
        form.fields['contract'].initial = contract
        return form

    def get_context_data(self, *args, **kwargs):
        kwargs['contract'] = ProjectContract.objects.get(id=int(self.kwargs['contract_id']))
        return super(AddContractBudget, self).get_context_data(*args, **kwargs)

    def get_success_url(self):
        return reverse('view_contract', args=(int(self.kwargs['contract_id']), ))

@cbv_decorator(permission_required('contracts.change_contractbudget'))
class EditContractBudget(UpdateView):
    model = ContractBudget
    form_class = CreateEditContractBudgetForm
    template_name = 'timepiece/contract/hour/create_edit.html'
    pk_url_kwarg = 'contract_budget_id'

    def get_form(self, *args, **kwargs):
        form = super(EditContractBudget, self).get_form(*args, **kwargs)
        form.fields['contract'].widget = widgets.HiddenInput()
        return form

    def get_context_data(self, *args, **kwargs):
        kwargs['contract'] = ProjectContract.objects.get(id=int(self.kwargs['contract_id']))
        return super(EditContractBudget, self).get_context_data(*args, **kwargs)

    def get_success_url(self):
        return reverse('view_contract', args=(int(self.kwargs['contract_id']), ))

@cbv_decorator(permission_required('contracts.delete_contractbudget'))
class DeleteContractBudget(DeleteView):
    model = ContractBudget
    template_name = 'timepiece/delete_object.html'
    pk_url_kwarg = 'contract_budget_id'

    def get_success_url(self):
        return reverse('view_contract', args=(int(self.kwargs['contract_id']), ))

@cbv_decorator(permission_required('contracts.add_contracthour'))
class AddContractHour(CreateView):
    model = ContractHour
    form_class = CreateEditContractHourForm
    template_name = 'timepiece/contract/hour/create_edit.html'

    def get_form(self, *args, **kwargs):
        form = super(AddContractHour, self).get_form(*args, **kwargs)
        form.fields['contract'].widget = widgets.HiddenInput()
        contract = ProjectContract.objects.get(
            id=int(self.kwargs['contract_id']))
        form.fields['contract'].initial = contract
        return form

    def get_context_data(self, *args, **kwargs):
        kwargs['contract'] = ProjectContract.objects.get(id=int(self.kwargs['contract_id']))
        return super(AddContractHour, self).get_context_data(*args, **kwargs)

    def get_success_url(self):
        return reverse('view_contract', args=(int(self.kwargs['contract_id']), ))

@cbv_decorator(permission_required('contracts.change_contracthour'))
class EditContractHour(UpdateView):
    model = ContractHour
    form_class = CreateEditContractHourForm
    template_name = 'timepiece/contract/hour/create_edit.html'
    pk_url_kwarg = 'contract_hours_id'

    def get_form(self, *args, **kwargs):
        form = super(EditContractHour, self).get_form(*args, **kwargs)
        form.fields['contract'].widget = widgets.HiddenInput()
        return form

    def get_context_data(self, *args, **kwargs):
        kwargs['contract'] = ProjectContract.objects.get(id=int(self.kwargs['contract_id']))
        return super(EditContractHour, self).get_context_data(*args, **kwargs)

    def get_success_url(self):
        return reverse('view_contract', args=(int(self.kwargs['contract_id']), ))

@cbv_decorator(permission_required('contracts.delete_contracthour'))
class DeleteContractHour(DeleteView):
    model = ContractHour
    template_name = 'timepiece/delete_object.html'
    pk_url_kwarg = 'contract_hours_id'

    def get_success_url(self):
        return reverse('view_contract', args=(int(self.kwargs['contract_id']), ))

@cbv_decorator(permission_required('contracts.add_contractrate'))
class AddContractRate(CreateView):
    model = ContractRate
    form_class = CreateEditContractRateForm
    template_name = 'timepiece/contract/rate/create_edit.html'

    def get_form(self, *args, **kwargs):
        form = super(AddContractRate, self).get_form(*args, **kwargs)
        form.fields['contract'].widget = widgets.HiddenInput()
        contract = ProjectContract.objects.get(
            id=int(self.kwargs['contract_id']))
        form.fields['contract'].initial = contract

        activity_id = self.request.GET.get('activity', None)
        if activity_id:
            form.fields['activity'].initial = Activity.objects.get(
                id=activity_id)

        form.fields['rate'].initial = contract.min_rate

        return form

    def get_context_data(self, *args, **kwargs):
        kwargs['contract'] = ProjectContract.objects.get(id=int(self.kwargs['contract_id']))
        return super(AddContractRate, self).get_context_data(*args, **kwargs)

    def get_success_url(self):
        return reverse('view_contract', args=(int(self.kwargs['contract_id']), ))

@cbv_decorator(permission_required('contracts.change_contractrate'))
class EditContractRate(UpdateView):
    model = ContractRate
    form_class = CreateEditContractRateForm
    template_name = 'timepiece/contract/rate/create_edit.html'
    pk_url_kwarg = 'contract_rate_id'

    def get_form(self, *args, **kwargs):
        form = super(EditContractRate, self).get_form(*args, **kwargs)
        form.fields['contract'].widget = widgets.HiddenInput()
        return form

    def get_context_data(self, *args, **kwargs):
        kwargs['contract'] = ProjectContract.objects.get(id=int(self.kwargs['contract_id']))
        return super(EditContractRate, self).get_context_data(*args, **kwargs)

    def get_success_url(self):
        return reverse('view_contract', args=(int(self.kwargs['contract_id']), ))

@cbv_decorator(permission_required('contracts.delete_contractrate'))
class DeleteContractRate(DeleteView):
    model = ContractRate
    template_name = 'timepiece/delete_object.html'
    pk_url_kwarg = 'contract_rate_id'

    def get_success_url(self):
        return reverse('view_contract', args=(int(self.kwargs['contract_id']), ))

@cbv_decorator(permission_required('contracts.add_contractnote'))
class AddContractNote(View):

    def post(self, request, *args, **kwargs):
        user = self.request.user
        contract = ProjectContract.objects.get(id=int(kwargs['contract_id']))
        note = ContractNote(contract=contract,
                            author=user,
                            text=request.POST.get('text', ''))
        if len(note.text):
            note.save()
        return HttpResponseRedirect(request.GET.get('next', None) or \
            reverse('view_contract', args=(contract.id,)))



@login_required #TODO correct permissions
def view_invoice_pdf(request, invoice_id):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="invoice.pdf"'
    styles = getSampleStyleSheet()

    invoice = EntryGroup.objects.get(pk=invoice_id)
    entries = invoice.entries
    contract = invoice.contract
    projects = contract.projects.all()
    project_0 = projects[0]
    client = project_0.business
    client_dept = project_0.business_department
    if not client_dept:
        client_dept=''
    else:
        client_dept=client_dept.name
    aac = Business.objects.get(short_name = 'AAC')
    invoice_date = formats.date_format(invoice.created, "SHORT_DATE_FORMAT")

    billable_entries = invoice.entries.filter(activity__billable=True)\
                                      .order_by('start_time')\
                                      .select_related()
    all_items = []

    total_bill = 0.00

    for p in projects:
        for r in contract.get_rates:
            hours=entries.filter(activity=r.activity, project=p).aggregate(tot_hours=Sum('hours'))['tot_hours'] #TODO this is dumb / ugly
            if not hours:
                continue
            rate=r.rate
            item_bill = hours*rate
            total_bill += float(item_bill)
            new_item = [invoice_date,contract.po_line_item, p.name+"\n"+r.activity.name,"{0:,.2f}".format(hours),"${0:,.2f}".format(rate),"${0:,.2f}".format(item_bill)]
            all_items.append(new_item)

    split_items=utils.chunk_list(all_items,9)




    ## find arial font ## todo file location static?
    font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Arial.ttf')
    pdfmetrics.registerFont(ttfonts.TTFont("Arial", font_path))

    c=canvas.Canvas(response, pagesize=letter)
    width, height = letter
    margin=inch/4
    width = width - margin
    height = height - margin



    pg_num =0
    for dummy_items in split_items:
        pg_num += 1
        #upper left logo
        img_w=2.27*inch
        img_h=1.38*inch

        # logo_path = static('images/aac_logo.jpg') # TODO why doesn't this work?
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'aac_logo.jpg')
        c.drawImage(logo_path,margin,height-img_h, width = img_w, height=img_h)

        #invoice upper right
        invoice_font_size=72
        invoice_x = width
        invoice_y = height - img_h

        c.setFont("Arial",invoice_font_size)
        c.setFillColorRGB(0.5,0.5,0.5)
        c.drawRightString(invoice_x,invoice_y,"INVOICE")

        #table upper right
        ur_table_data = [["INVOICE", invoice.auto_number],["PAGE","%d of %d" % (pg_num,len(split_items))],["DATE",invoice_date],["TERMS",contract.payment_terms],["PURCHASE ORDER",contract.po_number]]
        ur_table_font_size = 12

        ur_table = Table(data=ur_table_data)
        ur_table.setStyle(TableStyle([
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                ('ALIGN',(0,0),(-1,-1),'RIGHT')
            ]))
        ur_table.wrapOn(c,width, height)
        ur_table_w,ur_table_h = ur_table.wrap(0,0)

        ur_table_x = width-ur_table_w
        ur_table_y = invoice_y - ur_table_h - 0.25*inch

        ur_table.drawOn(c,ur_table_x,ur_table_y)

        c.setFont("Arial",ur_table_font_size)


        # AAC Address TABLE
        add_table_data = [[aac.name],[aac.billing_street],[aac.billing_city+", "+aac.billing_state+" "+aac.billing_postalcode],["AR@aacengineering.com"],["(888) 290-5878"],[" "],["TAX ID: 27-0673181"]]
        add_table_font_size = 12

        add_table = Table(data=add_table_data)
        add_table.setStyle(TableStyle([
                ('ALIGN',(0,0),(-1,-1),'RIGHT')
            ]))

        add_table.wrapOn(c,width, height)
        add_table_w,add_table_h = add_table.wrap(0,0)

        add_table_x = margin
        add_table_y = invoice_y - add_table_h - 0.25*inch

        add_table.drawOn(c,add_table_x,add_table_y)

        c.setFont("Arial",add_table_font_size)


        # divider line between aac and customer Address
        div_add_x = add_table_x + add_table_w + 0.25*inch
        div_shift = 0.125*inch
        c.line(div_add_x, add_table_y-div_shift, div_add_x, invoice_y-div_shift)


        # client address
        add_client_table_data = [[""]]
        add_client_table_data.append([client.name])
        if client_dept != '':
            add_client_table_data.append([client_dept])
        add_client_table_data.append([client.billing_street])
        if client.billing_street_2:
            add_client_table_data.append([client.billing_street_2])
        add_client_table_data.append([client.billing_city+", "+client.billing_state+" "+client.billing_postalcode])
        add_client_table_data.append([" "])

        add_client_table_font_size = 12

        add_client_table = Table(data=add_client_table_data)
        add_client_table.setStyle(TableStyle([
                ('ALIGN',(0,0),(-1,-1),'LEFT')
            ]))

        add_client_table.wrapOn(c,width, height)
        add_client_table_w,add_client_table_h = add_client_table.wrap(0,0)

        add_client_table_x = div_add_x + 0.25*inch
        add_client_table_y = invoice_y - add_client_table_h - 0.25*inch

        add_client_table.drawOn(c,add_client_table_x,add_client_table_y)

        c.setFont("Arial",add_client_table_font_size)


        #table lowerright
        lr_table_data = [["TOTAL", "${0:,.2f}".format(total_bill)],["PAYMENTS/CREDITS","-"],["BALANCE DUE","${0:,.2f}".format(total_bill)]]
        lr_table_font_size = 12

        lr_table = Table(data=lr_table_data)
        lr_table.setStyle(TableStyle([
                ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                ('ALIGN',(0,0),(-1,-1),'RIGHT')
            ]))
        lr_table.wrapOn(c,width, height)
        lr_table_w,lr_table_h = lr_table.wrap(0,0)

        lr_table_x = width-lr_table_w
        lr_table_y = margin

        lr_table.drawOn(c,lr_table_x,lr_table_y)

        c.setFont("Arial",lr_table_font_size)

        #table lowerleft
        ll_table_data = [["Please make all checks payable to: AAC Engineering"],["We greatly appreciate your business!"]]
        ll_table_font_size = 12

        ll_table = Table(data=ll_table_data)
        ll_table.setStyle(TableStyle([
                ('ALIGN',(0,0),(-1,-1),'LEFT')
            ]))
        ll_table.wrapOn(c,width, height)
        ll_table_w,ll_table_h = ll_table.wrap(0,0)

        ll_table_x = margin
        ll_table_y = margin

        ll_table.drawOn(c,ll_table_x,ll_table_y)

        c.setFont("Arial",ll_table_font_size)


        # invoice items
        invoice_items_table_data = [["Date","Line Item","Description","Quantity","Rate","Amount"]]

        # dummy_items = [["12/12/12","1",Paragraph("We did lots! Something Great That you should pay lots of money for",styles['Normal']),"999999","$125.00","$9,999,999.99"],
        #                 ["12/12/12","2",Paragraph("We Did more!. Something Great That you should pay lots of money for",styles['Normal']),"999999","$125.00","$9,999,999.99"]]




        for item in dummy_items:
            invoice_items_table_data.append(item)


        invoice_items_table_font_size = 12
        c.setFont("Arial",invoice_items_table_font_size)

        space_h = (add_table_y) - (margin + lr_table_h + 0.25*inch)
        cww=width-margin
        it_cw_ratio=[3,3,11,3,3,4]
        it_cw_d=sum(it_cw_ratio)*1.0

        it_cw = []
        for zz in it_cw_ratio:
            it_cw.append(int(round(cww*zz/it_cw_d)))

        # it_cw = [cww*3/25.0,width*1/25.0,width*9/25.0,width*3/25.0,width*3/25.0,width*6/25.0]
        hh=invoice_items_table_font_size+10
        rh=invoice_items_table_font_size*2+10
        rows_to_add = int(math.floor((space_h-hh)/(rh*1.0)))-len(invoice_items_table_data)


        invoice_items_table_data.extend([[""]*len(invoice_items_table_data[0])]*rows_to_add)
        it_rh = [hh]+[rh]*(len(invoice_items_table_data)-1)


        invoice_items_table = Table(data=invoice_items_table_data,colWidths = it_cw, rowHeights=it_rh)
        invoice_items_table.setStyle(TableStyle([
                ('BOX', (0,0), (-1,0), 0.25, colors.black),
                ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                ('ALIGN',(0,0),(-1,-1),'RIGHT')
            ]))

        invoice_items_table.wrap(width, height)
        #invoice_items_table_w,invoice_items_table_h = invoice_items_table.wrap(0,0)

        invoice_items_table_x = margin
        invoice_items_table_y = margin + lr_table_h + 0.25*inch

        invoice_items_table.drawOn(c,invoice_items_table_x,invoice_items_table_y)

        c.setFont("Arial",invoice_items_table_font_size)

        #generate and save
        c.showPage()




    c.save()

    return response




@login_required
@transaction.commit_on_success
def create_invoice(request):
    pk = request.GET.get('project', None)
    single_project=True
    if not pk:
        single_project=False
        pk = request.GET.get('contract', None)

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


    initial = {
        'user': request.user,
        'from_date': from_date,
        'to_date': to_date,
    }
    entries_query = {
        'status': Entry.APPROVED,
        'end_time__lt': to_date + relativedelta(days=1),
    }

    if single_project:
        project = get_object_or_404(Project, pk=pk)
        initial.update({'project': project,'single_project': single_project})
        entries_query.update({'project__id': project.id})
    else:
        contract = get_object_or_404(ProjectContract, pk=pk)
        initial.update({'contract': contract,'single_project': single_project})
        entries_query.update({'project__in': contract.projects.all})

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

    context = {
        'invoice_form': invoice_form,
        'billable_entries': billable_entries,
        'nonbillable_entries': nonbillable_entries,
        'billable_totals': HourGroup.objects
            .summaries(billable_entries),
        'nonbillable_totals': HourGroup.objects
            .summaries(nonbillable_entries),
        'from_date': from_date,
        'to_date': to_date,
    }

    if single_project:
        context.update({'single_project':True,'project': project})
    else:
        context.update({'single_project':False,'contract':contract})

    return render(request, 'timepiece/invoice/create.html', context)


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
        grouping = form_data['invoice_grouping']
        dates = Q()
        dates &= Q(end_time__gte=from_date) if from_date else Q()
        dates &= Q(end_time__lt=to_date) if to_date else Q()

        billable = Q(project__type__billable=True, project__status__billable=True)
        entry_status = Q(status=Entry.APPROVED)
        project_status = Q(project__status__in=statuses)\
                if statuses is not None else Q()
        # Calculate hours for each project
        if grouping == 'by_project':
            ordering = ('project__type__label', 'project__status__label',
                    'project__business__name', 'project__name', 'status')
        else:
            ordering = ('project__type__label', 'project__business__name',
                    'project__contracts__name', 'project__name', 'status')
        project_totals = Entry.objects.filter(
            dates, billable, entry_status, project_status).order_by(*ordering)
        # Find users with unverified/unapproved entries to warn invoice creator
        date_range_entries = Entry.objects.filter(dates)
        user_values = ['user__pk', 'user__first_name', 'user__last_name']
        unverified = date_range_entries.filter(
            status=Entry.UNVERIFIED).values_list(*user_values).order_by('user__first_name').distinct()
        unapproved = date_range_entries.filter(
            status=Entry.VERIFIED).values_list(*user_values).order_by('user__first_name').distinct()
    else:
        project_totals = unverified = unapproved = Entry.objects.none()
    return render(request, 'timepiece/invoice/outstanding.html', {
        'date_form': form,
        'project_totals': project_totals,
        'unverified': unverified,
        'unapproved': unapproved,
        'to_date': form.get_to_date(),
        'from_date': form.get_from_date(),
        'invoice_grouping':form.get_invoice_grouping(),
    })


@cbv_decorator(permission_required('contracts.add_entrygroup'))
class ListInvoices(SearchListView):
    model = EntryGroup
    search_fields = ['user__username__icontains', 'project__name__icontains',
            'comments__icontains', 'number__icontains','contract__name__icontains','auto_number__icontains']
    template_name = 'timepiece/invoice/list.html'


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
            'contract': invoice.contract,
            'single_project': invoice.single_project,
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
            'single_project':invoice.single_project,
            'user': request.user,
            'from_date': invoice.start,
            'to_date': invoice.end,
        }

        if invoice.single_project:
            initial.update({'project': invoice.project})
        else:
            inital.update({'contract': invoice.contract})

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

import sys, traceback
@csrf_exempt
# @permission_required('contracts.add_contractattachment')
def contract_s3_attachment(request, contract_id):
    bucket = request.POST.get('bucket', None)
    uuid = request.POST.get('key', None)
    userid = int(request.POST.get('firmbase-userid', 4))
    filename = request.POST.get('name', '')

    attachment = ContractAttachment(
        contract=ProjectContract.objects.get(id=int(contract_id)),
        bucket=bucket,
        uuid=uuid,
        filename=filename,
        uploader=User.objects.get(id=userid))
    attachment.save()

    return HttpResponse(status=200)

@permission_required('contracts.add_contractattachment')
def contract_upload_attachment(request, contract_id):
    try:
        afu = AjaxFileUploader(MongoDBUploadBackend, db='contract_attachments')
        hr = afu(request)
        content = json.loads(hr.content)
        memo = {'uploader': str(request.user),
                'file_id': str(content['_id']),
                'upload_time': str(datetime.datetime.now()),
                'filename': content['filename']}
        memo.update(content)

        # save attachment to ticket
        attachment = ContractAttachment(
            contract=ProjectContract.objects.get(id=int(contract_id)),
            file_id=str(content['_id']),
            filename=content['filename'],
            upload_datetime=datetime.datetime.now(),
            uploader=request.user,
            description='n/a')
        attachment.save()
        return HttpResponse(json.dumps(memo),
                            content_type="application/json")
    except:
        print sys.exc_info(), traceback.format_exc()
    return hr

@permission_required('contracts.view_contractattachment')
def contract_download_attachment(request, contract_id, attachment_id):
    print 'download contract attachment?', contract_id, attachment_id
    try:
        print 'hello world 1'
        contract_attachment = ContractAttachment.objects.get(
            contract_id=contract_id, id=attachment_id)
        print 'ca', contract_attachment
        return HttpResponseRedirect(contract_attachment.get_download_url())
    except:
        print sys.exc_info(), traceback.format_exc()
        return HttpResponse('Contract attachment could not be found.')

@permission_required('contracts.delete_contractattachment')
def contract_delete_attachment(request, contract_id, attachment_id):
    try:
        contract_attachment = ContractAttachment.objects.get(
            contract_id=int(contract_id), uuid=attachment_id)
        contract_attachment.delete()
        return HttpResponse(status=204)
    except:
        return HttpResponse('Attachment could not be found.')
