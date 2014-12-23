from django.conf.urls import patterns, url

from timepiece.contracts import views


urlpatterns = patterns('',
    # Contracts
    url(r'^contract/$',
        views.ContractList.as_view(),
        name='list_contracts'),
    url(r'^contract/(?P<contract_id>\d+)/$',
        views.ContractDetail.as_view(),
        name='view_contract'),

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
