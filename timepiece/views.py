import csv

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from timepiece.forms import QuickSearchForm


@login_required
def search(request):
    form = QuickSearchForm(request.GET or None)
    if form.is_valid():
        return HttpResponseRedirect(form.save())
    return render(request, 'timepiece/search_results.html', {
        'form': form,
    })


class CSVMixin(object):

    def render_to_response(self, context):
        response = HttpResponse(content_type='text/csv')
        fn = self.get_filename(context)
        response['Content-Disposition'] = 'attachment; filename=%s.csv' % fn
        rows = self.convert_context_to_csv(context)
        writer = csv.writer(response)
        for row in rows:
            writer.writerow(row)
        return response

    def get_filename(self, context):
        raise NotImplemented('You must implement this in the subclass')

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file"""
        raise NotImplemented('You must implement this in the subclass')
