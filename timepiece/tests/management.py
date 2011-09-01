import datetime
import re
from StringIO import StringIO
from dateutil.relativedelta import relativedelta

from django.core.urlresolvers import reverse
from django.contrib.auth.models import User, Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command

from timepiece.tests.base import TimepieceDataTestCase

from timepiece import models as timepiece
from timepiece import forms as timepiece_forms
from timepiece import utils
from timepiece.management.commands import check_entries


class CheckEntries(TimepieceDataTestCase):
    def setUp(self):
        super(CheckEntries, self).setUp()
        self.default_data = {
            'user': self.user,
            'project': self.project,
            'seconds_paused': 0,
            'status': 'verified',
        }
        self.good_start = datetime.datetime.now() - datetime.timedelta(days=0, hours=8)
        self.good_end = datetime.datetime.now() - datetime.timedelta(days=0)
        self.bad_start = datetime.datetime.now() - datetime.timedelta(days=1, hours=8)
        self.bad_end = datetime.datetime.now() - datetime.timedelta(days=1)
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
            #Range uses 1 so that good_start/good_end use today as valid times.
            for day in range(1, 80):
                self.default_data.update({
                    'start_time': datetime.datetime.now() - datetime.timedelta(days=day, hours=8),
                    'end_time': datetime.datetime.now() - datetime.timedelta(days=day,),
                })
                self.create_entry(self.default_data)        
#        print timepiece.Entry.objects.all()

    #helper functions
    buffer_dict = {}
    def check(self, *args, **kwargs):
        output = err = StringIO()
        call_command('check_entries', *args, stdout=output, stderr=err, **kwargs)
        output.seek(0)
        err.seek(0)
        out = output.read()
        overlap = re.findall('Entry.*', out)
        out_list = out.split('\n')
        err_list = err.read().split('\n')
        self.buffer_dict = {
            'out': out_list,
            'err': err_list,
            'overlap': overlap,
        }
        return self.buffer_dict

    def get_output(self, dict_in=buffer_dict):
        return dict_in.get('out', [])
    
    def get_err(self, dict_in=buffer_dict):
        return dict_in.get('err', [])

    def show_output(self, dict_in=buffer_dict):
        for string in self.get_output(dict_in):
            print string

    def show_err(self, dict_in=buffer_dict):
        for string in self.get_err(dict_in):
            print string

    def make_entry(self, **kwargs):
        valid = kwargs.get('valid', True)
        if valid:
            default_start = self.good_start
            default_end = self.good_end
        else:
            default_start = self.bad_start
            default_end = self.bad_end
        user = kwargs.get('user', self.user)
        start = kwargs.get('start_time', default_start)
        end = kwargs.get('end_time', default_end)
        data = self.default_data
        data.update({
            'user': user,
            'start_time': start,
            'end_time': end,
        })
        self.create_entry(data)

    #tests
    def testFindStart(self):
        #Establish some datetimes
        now = datetime.datetime.now()
        today = now - relativedelta(
            hour=0, minute=0, second=0, microsecond=0)
        last_billing = today - relativedelta(months=1, day=1)
        yesterday = today - relativedelta(days=1)
        ten_days_ago = today - relativedelta(days=10)
        thisweek = utils.get_week_start(today)
        thismonth = today - relativedelta(day=1)
        thisyear = today - relativedelta(month=1, day=1)
        #Use command flags to obtain datetimes
        start_default = check_entries.Command().find_start()
        start_yesterday = check_entries.Command().find_start(days=1)
        start_ten_days_ago = check_entries.Command().find_start(days=10)
        start_of_week = check_entries.Command().find_start(week=True)
        start_of_month = check_entries.Command().find_start(month=True)
        start_of_year = check_entries.Command().find_start(year=True)
        #assure the returned datetimes are correct
        self.assertEqual(start_default, last_billing)
        self.assertEqual(start_yesterday, yesterday)
        self.assertEqual(start_ten_days_ago, ten_days_ago)
        self.assertEqual(start_of_week, thisweek)
        self.assertEqual(start_of_month, thismonth)
        self.assertEqual(start_of_year, thisyear)

    def testFindPeople(self):
        #Find one person by icontains first or last name, return all if no args
        people1 = check_entries.Command().find_people('firsT1')
        people2 = check_entries.Command().find_people('LasT2')
        all_people = check_entries.Command().find_people()
        #obtain instances from the querysets
        person1 = people1.get(pk=self.user.pk)
        person2 = people2.get(pk=self.user2.pk)
        all_1 = all_people.get(pk=self.user.pk)
        all_2 = all_people.get(pk=self.user2.pk)
        all_3 = all_people.get(pk=self.superuser.pk)
        self.assertEqual(people1.count(), 1)
        self.assertEqual(people2.count(), 1)
        self.assertEqual(all_people.count(), 3)
        self.assertEqual(person1, self.user)
        self.assertEqual(person2, self.user2)
        self.assertEqual(all_1, person1)
        self.assertEqual(all_2, person2)
        self.assertEqual(all_3, self.superuser)

    def testFindEntries(self):
        start = check_entries.Command().find_start()
        all_people = check_entries.Command().find_people()
        entries = check_entries.Command().find_entries(all_people, start)
        self.make_entry(valid=False)
        all_overlaps = 0
        while True:
            try:
                person_entries = entries.next()
            except StopIteration:
                print all_overlaps
                return
            else:
                user_total_overlaps = check_entries.Command().check_entry(
                    person_entries, verbosity=2)
                all_overlaps += user_total_overlaps

    def testCheckOverlap(self):
        #define start and end times relative to a valid entry
        a_start_before = self.good_start - datetime.timedelta(minutes=5)
        a_start_inside = self.good_start + datetime.timedelta(minutes=5)
        a_end_inside = self.good_start + datetime.timedelta(minutes=5)
        a_end_after = self.good_end + datetime.timedelta(minutes=5)
        #Create a valid entry for today
        self.make_entry(valid=True)

        #Create a bad entry starting inside the valid one
        self.make_entry(start_time=a_start_inside, end_time=a_end_after)
        #Create a bad entry ending inside the valid one
        self.make_entry(start_time=a_start_before, end_time=a_end_after)
        #Create a bad entry that starts and ends outside a valid one
        self.make_entry(start_time=a_start_inside, end_time=a_end_inside)
        #Create a bad entry that starts and ends inside a valid one
        self.make_entry(start_time=a_start_before, end_time=a_end_after)

        entries = timepiece.Entry.objects.filter(user=self.user)
        user_total_overlaps = 0
        for index_a, entry_a in enumerate(entries):
            for index_b in range(index_a, len(entries)):
                entry_b = entries[index_b]
                if entry_a.check_overlap(entry_b):                    
                    user_total_overlaps += 1
#                    print 'Conflict with %s and %s' % (entry_a, entry_b)

#                    check_entries.Command().show_overlap(entry_a, entry_b)
#                    self.show_overlap(entry_a, entry_b)

        
#    def testAllEntries(self):
#        self.default_data.update({
#            'start_time': datetime.datetime.now() - datetime.timedelta(days=0, hours=8),
#            'end_time': datetime.datetime.now() - datetime.timedelta(days=0,),
#        })
#        self.create_entry(self.default_data)
#        bars = check_1_2 = self.check('first1', 'first2', verbosity=2)
#        self.show_output(bars)
#        print bars['overlap']
