from django.conf.urls import patterns, url

from timepiece.contracts import views


urlpatterns = patterns('',

    # Contracts
    url(r'^contract/$',
        views.ContractList.as_view(),
        name='list_contracts'),
    url(r'^contract/create/$',
        views.CreateContract.as_view(),
        name='create_contract'),
    url(r'^contract/(?P<contract_id>\d+)/$',
        views.ContractDetail.as_view(),
        name='view_contract'),
    url(r'^contract/(?P<contract_id>\d+)/edit/$',
        views.EditContract.as_view(),
        name='edit_contract'),
    url(r'^contract/(?P<contract_id>\d+)/delete/$',
        views.DeleteContract.as_view(),
        name='delete_contract'),

    # General Tasks
    # Add General Task
    url(r'^contract/(?P<contract_id>\d+)/add-general-task$',
        views.AddContractGeneralTask.as_view(),
        name='contract_add_general_task'),
    # Remove General Task
    url(r'^contract/(?P<contract_id>\d+)/remove-general-task$',
        views.RemoveContractGeneralTask.as_view(),
        name='contract_remove_general_task'),

    # Get Tags / Add Tag
    url(r'^contract/(?P<contract_id>\d+)/tags/$',
        views.ContractTags.as_view(),
        name='contract_tags'),
    # Remove Tag
    url(r'^contract/(?P<contract_id>\d+)/tags/remove$',
        views.RemoveContractTag.as_view(),
        name='remove_contract_tag'),

    # Add Contract Note
    url(r'^contract/(?P<contract_id>\d+)/add_note$', # expects querystring of transition_id=<int>
        views.AddContractNote.as_view(),
        name='add_contract_note'),

    # Contract Atachments
    url(r'^contract/(?P<contract_id>\d+)/attachment/add/$',
        views.contract_upload_attachment,
        name='add_contract_attachment'),
    url(r'^contract/(?P<contract_id>\d+)/attachment/s3/$',
        views.contract_s3_attachment,
        name='s3_contract_attachment'),
    url(r'^contract/(?P<contract_id>\d+)/attachment/(?P<attachment_id>\d+)/$',
        views.contract_download_attachment,
        name='download_contract_attachment'),
    url(r'^contract/(?P<contract_id>\d+)/attachment/(?P<attachment_id>[\w\-\.]+)/delete$',
        views.contract_delete_attachment,
        name='delete_contract_attachment'),


    # Contract Increment (Budget and Hours)
    url(r'^contract/(?P<contract_id>\d+)/increment/$',
        views.add_contract_increment,
        name='add_contract_increment'),

    url(r'^contract/(?P<contract_id>\d+)/budget/$',
        views.AddContractBudget.as_view(),
        name='add_contract_budget'),
    url(r'^contract/(?P<contract_id>\d+)/budget/(?P<contract_budget_id>\d+)/edit/$',
        views.EditContractBudget.as_view(),
        name='edit_contract_budget'),
    url(r'^contract/(?P<contract_id>\d+)/budget/(?P<contract_budget_id>\d+)/delete/$',
        views.DeleteContractBudget.as_view(),
        name='delete_contract_budget'),

    url(r'^contract/(?P<contract_id>\d+)/hours/$',
        views.AddContractHour.as_view(),
        name='add_contract_hours'),
    url(r'^contract/(?P<contract_id>\d+)/hours/(?P<contract_hours_id>\d+)/edit/$',
        views.EditContractHour.as_view(),
        name='edit_contract_hours'),
    url(r'^contract/(?P<contract_id>\d+)/hours/(?P<contract_hours_id>\d+)/delete/$',
        views.DeleteContractHour.as_view(),
        name='delete_contract_hours'),

    # Contract Rates
    url(r'^contract/(?P<contract_id>\d+)/rate/$',
        views.AddContractRate.as_view(),
        name='add_contract_rate'),
    url(r'^contract/(?P<contract_id>\d+)/rate/(?P<contract_rate_id>\d+)/edit/$',
        views.EditContractRate.as_view(),
        name='edit_contract_rate'),
    url(r'^contract/(?P<contract_id>\d+)/rate/(?P<contract_rate_id>\d+)/delete/$',
        views.DeleteContractRate.as_view(),
        name='delete_contract_rate'),


    # Invoices
    url(r'invoice/$',
        views.ListInvoices.as_view(),
        name='list_invoices'),
    url(r'invoice/outstanding/$',
        views.list_outstanding_invoices,
        name='list_outstanding_invoices'),
    url(r'invoice/create/$',
        views.create_invoice,
        name='create_invoice'),
    url(r'invoice/(?P<invoice_id>\d+)/$',
        views.InvoiceDetail.as_view(),
        name='view_invoice'),
    url(r'invoice/(?P<invoice_id>\d+)/csv/$',
        views.InvoiceDetailCSV.as_view(),
        name='view_invoice_csv'),
    url(r'invoice/(?P<invoice_id>\d+)/pdf/$',
        views.view_invoice_pdf,
        name='view_invoice_pdf'),
    url(r'invoice/(?P<invoice_id>\d+)/entries/$',
        views.InvoiceEntriesDetail.as_view(),
        name='view_invoice_entries'),
    url(r'invoice/(?P<invoice_id>\d+)/entries/(?P<entry_id>\d+)/remove/$',
        views.delete_invoice_entry,
        name='delete_invoice_entry'),
    url(r'invoice/(?P<invoice_id>\d+)/edit/$',
        views.InvoiceEdit.as_view(),
        name='edit_invoice'),
    url(r'invoice/(?P<invoice_id>\d+)/delete/$',
        views.InvoiceDelete.as_view(),
        name='delete_invoice'),
)
