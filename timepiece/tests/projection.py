import datetime
from decimal import Decimal

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import Sum

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms
from timepiece.tests.base import TimepieceDataTestCase

from dateutil import relativedelta

from timepiece.projection import run_projection


class ProjectionTest(TimepieceDataTestCase):

    def testHours(self):
        pc1 = self.create_project_contract({'num_hours': 100})
        ca1 = self.create_contract_assignment({'contract': pc1,
                                               'num_hours': 100})
        run_projection()
        self.assertEqual(100, ca1.blocks.aggregate(s=Sum('hours'))['s'])

