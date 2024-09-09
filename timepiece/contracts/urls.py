from django.urls import re_path

from timepiece.contracts import views


urlpatterns = [
    # Contracts
    re_path(r'^contract/$',
            views.ContractList.as_view(),
            name='list_contracts'),
    re_path(r'^contract/(?P<contract_id>\d+)/$',
            views.ContractDetail.as_view(),
            name='view_contract'),

    # Invoices
    re_path(r'invoice/$',
            views.ListInvoices.as_view(),
            name='list_invoices'),
    re_path(r'invoice/outstanding/$',
            views.list_outstanding_invoices,
            name='list_outstanding_invoices'),
    re_path(r'invoice/create/$',
            views.create_invoice,
            name='create_invoice'),
    re_path(r'invoice/(?P<invoice_id>\d+)/$',
            views.InvoiceDetail.as_view(),
            name='view_invoice'),
    re_path(r'invoice/(?P<invoice_id>\d+)/csv/$',
            views.InvoiceDetailCSV.as_view(),
            name='view_invoice_csv'),
    re_path(r'invoice/(?P<invoice_id>\d+)/entries/$',
            views.InvoiceEntriesDetail.as_view(),
            name='view_invoice_entries'),
    re_path(r'invoice/(?P<invoice_id>\d+)/entries/(?P<entry_id>\d+)/remove/$',
            views.delete_invoice_entry,
            name='delete_invoice_entry'),
    re_path(r'invoice/(?P<invoice_id>\d+)/edit/$',
            views.InvoiceEdit.as_view(),
            name='edit_invoice'),
    re_path(r'invoice/(?P<invoice_id>\d+)/delete/$',
            views.InvoiceDelete.as_view(),
            name='delete_invoice'),
]
