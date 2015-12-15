from __future__ import absolute_import

import csv
from decimal import Decimal
from json import JSONEncoder

from django.http import HttpResponse


class DecimalEncoder(JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


class CSVViewMixin(object):

    def render_to_response(self, context):
        response = HttpResponse(content_type='text/csv')
        fn = self.get_filename(context)
        response['Content-Disposition'] = 'attachment; filename="%s.csv"' % fn
        rows = self.convert_context_to_csv(context)
        writer = csv.writer(response)
        for row in rows:
            try:
                writer.writerow(row)
            except:
                new_row = []
                for item in row:
                    try:
                        new_row.append(str(item).encode('ascii'))
                    except:
                        new_row.append('ERROR: There is a special character '
                            'in this field.  Remove the special character(s) '
                            'using FirmBase and re-export.')
                writer.writerow(new_row)
        return response

    def get_filename(self, context):
        raise NotImplemented('You must implement this in the subclass')

    def convert_context_to_csv(self, context):
        """Convert the context dictionary into a CSV file."""
        raise NotImplemented('You must implement this in the subclass')
