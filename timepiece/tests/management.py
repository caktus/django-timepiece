import datetime
import re
from StringIO import StringIO

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command

from timepiece.tests.base import TimepieceDataTestCase

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms
from timepiece.management.commands import check_entries

possible_args = [
    '--thisweek', 
    '--thismonth', 
    '-y', '--thisyear', 
    '-a', '--all', '--forever',
    '-d', '--days',
]

class CheckEntries(TimepieceDataTestCase):
    def setUp(self):
        super(CheckEntries, self).setUp()
        self.default_data = {
            'user': self.user,
            'project': self.project,
            'seconds_paused': 0,
            'status': 'verified',
        }
        #Create users for the test
        self.user.first_name = 'first1'
        self.user.last_name = 'last1'
        self.user.save()
        
        self.user2.first_name = 'first2'
        self.user2.last_name = 'last2'
        self.user2.save()

        #Create a list of valid entries.
        #Test cases may create overlapping entries later
        for user in [self.user, self.user2]:
            self.default_data.update({
                'user': user,
            })
            for day in range(0, 80):
                self.default_data.update({
                    'start_time': datetime.datetime.now() - datetime.timedelta(days=day, hours=8),
                    'end_time': datetime.datetime.now() - datetime.timedelta(days=day,),
                })
                self.create_entry(self.default_data)        
#        print timepiece.Entry.objects.all()

    #helper functions
    buffer_dict = {}
    overlap_cp = re.compile(
        '(?P<entry>\d+) for ' + \
        '(?P<first>\w+) (?P<last>\w+) from ' + \
        '(?P<start_time_str>\d+-\d+-\d+ \d+:\d+:\d+.\d+) to ' + \
        '(?P<end_time_str>\d+-\d+-\d+ \d+:\d+:\d+.\d+) on ' + \
        '(?P<project>\w+)',
    )

    def overlaps_to_dict(self, tupe_in):
        dict_out = {
            'entry': tupe_in[0],
            'first_name': tupe_in[1],
            'last_name': tupe_in[2],
            'start_time_str': tupe_in[3],
            'end_time_str': tupe_in[4],
            'project': tupe_in[5],
        }
        return dict_out

    def check(self, *args, **kwargs):
        output = err = StringIO()
        call_command('check_entries', *args, stdout=output, stderr=err, **kwargs)
        output.seek(0)
        err.seek(0)
        out = output.read()
        overlap_tupes = self.overlap_cp.findall(out)
        overlaps = []
        for tupe in overlap_tupes:
            overlaps.append(self.overlaps_to_dict(tupe))
        out_list = out.split('\n')
        err_list = err.read().split('\n')
        self.buffer_dict = {
            'out': out_list,
            'err': err_list,
            'overlap': overlaps
        }
        return self.buffer_dict

    def get_output(self, dict_in=buffer_dict):
        return dict_in.get('out', [])
    
    def get_err(self, dict_in=buffer_dict):
        return dict_in.get('err', [])

    def get_overlap(self, dict_in=buffer_dict):
        return dict_in.get('overlap', [])

    def show_output(self, dict_in=buffer_dict):
        for string in self.get_output(dict_in):
            print string

    def show_err(self, dict_in=buffer_dict):
        for string in self.get_err(dict_in):
            print string

    def show_overlap(self, dict_in=buffer_dict):
        for dict_item in self.get_overlap(dict_in):
            print dict_item.items()

    def testAllEntries(self):
        self.default_data.update({
            'start_time': datetime.datetime.now() - datetime.timedelta(days=0, hours=8),
            'end_time': datetime.datetime.now() - datetime.timedelta(days=0,),
        })
        self.create_entry(self.default_data)
#        check_1 = self.check('first1', verbosity=2)
#        check_2 = self.check('first2', verbosity=2)
        check_1_2 = self.check('first1', 'first2', verbosity=2)
        foos = self.get_overlap(check_1_2)
#        print foos[0].get('entry', '')
#        print check_1_2['out']
