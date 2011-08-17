import pprint
import datetime
from optparse import OptionParser, make_option

from dateutil.relativedelta import relativedelta

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import models as auth_models
from django.db.models import Q
from django.conf import settings
from django.db import transaction

from timepiece import utils

from timepiece import models as timepiece


class Command(BaseCommand):
    args = '<user\'s first or last name or user.id> <user\'s first...>...'
    help = 'Check the database for entries that overlap. Use --help for options'
    
    parser = OptionParser()
    parser.usage += """
        To check all users:
        ./manage.py check_entries [OPTIONS]
        or
        ./manage.py check_entries <first or last name1> <name2>...<name n> [OPTIONS]
        
        For options type:
        ./manage.py check_entries --help
    """
    option_list = BaseCommand.option_list + (
        make_option('--thisweek',
            action='store_true',
            dest='week',
            default=False,
            help='Show entries from this week only'),
        ) +(
        make_option('--thismonth',
            action='store_true',
            dest = 'month',
            default = False,
            help='Show entries from this month only'),
        ) +(
        make_option('-y', '--thisyear',
            action='store_true',
            dest = 'year',
            default = False,
            help = 'Show entries from this year only'),
        ) +(
        make_option('-a', '--all', '--forever',
            action='store_true',
            dest = 'all',
            default= False,
            help = 'Show entries from all recorded history'),
        )+(
        make_option('-d', '--days',
            dest = 'days',
            type = 'int',
            default = 0,
            help='Show entries for the last n days only'),
        )
    parser.add_options(option_list)
    (options, args) = parser.parse_args()  

    def handle(self, *args, **options):
            
        #If no flags, set to 3 months ago
        start = datetime.datetime.now() - datetime.timedelta(weeks=8)
        #Set the start date based on arguments provided through options
        if self.options.week:
            start = utils.get_week_start()
        if self.options.month:
            start = datetime.datetime.now() - relativedelta(day=1)
        if self.options.year:
            start = datetime.datetime.now() - relativedelta(day=1, month=1)
        if self.options.days:
            start = datetime.datetime.now() - datetime.timedelta(days=self.options.days)
            
        if self.options.all:
            print("Checking overlaps from the beginning of time")
        else:    
            print("Checking overlap starting at: " + str(start))     
        
        #If no args given, check every user
        if args: 
            all_flag = False
            names = reduce(lambda query, arg: query | (Q(first_name__icontains=arg) | Q(last_name__icontains=arg)), args, Q())                        
            people = auth_models.User.objects.filter(names)
        else:
            all_flag = True
            people = auth_models.User.objects.all()            
            
        if not people.count() and not all_flag:
            print("No user found with that name")
            quit()

        for person in people:                        
            if self.options.all:
                entries = timepiece.Entry.objects.filter(user=person).order_by('start_time')
            else:
                entries = timepiece.Entry.objects.filter(user=person, start_time__gte=start).order_by('start_time')
                           
            if not entries.count() or not all_flag: 
                print('Checking %s %s...') % (person.first_name, person.last_name)
            
            for entry in entries:                   
                if entry.is_overlapping():
                    data = {
                        'first_name':person.first_name, 'last_name':person.last_name, 
                        'entry':entry.id, 
                        'start_time':entry.start_time, 'end_time':entry.end_time,
                        'project':entry.project
                    }
                    print(output(data))


def output(data):
    return "Entry %(entry)d for %(first_name)s %(last_name)s from %(start_time)s to %(end_time)s on %(project)s overlaps another entry" % data
                       
           
                 
