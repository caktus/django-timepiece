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
        ./manage.py check_entries <arg1> <arg2>...<argn> [OPTIONS]
            where argn is = first name, last name or user.id
        
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
        make_option('-d', '--days',
            dest = 'days',
            type = 'int',
            default = 0,
            help='Show entries for the last n days only'),
        )
    parser.add_options(option_list)
    (options, args) = parser.parse_args()  

    def handle(self, *args, **options):
        #If no args given, check every user
        if not args: 
            all_flag = True
            last = auth_models.User.objects.latest('pk')
            args = range(0, last.pk + 1)
        else:
            all_flag = False
            
        #If no flags, set to 3 months ago
        start = datetime.datetime.now() - datetime.timedelta(weeks = 8)
        #Set the start date based on arguments provided through options
        if self.options.week:
            start = utils.get_week_start()
        if self.options.month:
            start = datetime.datetime.now() - relativedelta(day = 1)
        if self.options.year:
            start = datetime.datetime.now() - relativedelta(day = 1, month = 1)
        if self.options.days:
            start = datetime.datetime.now() - datetime.timedelta(days = self.options.days)
        self.stdout.write('\n' + "Checking overlap starting at: " + str(start) + '\n')
        
        overlap_names = []
        for arg in args:
            #use id's otherwise search for the name
            try:
                people = auth_models.User.objects.filter(pk=arg)
                
            except:                
                people = auth_models.User.objects.filter(
                    Q(first_name__icontains=arg) |
                    Q(last_name__icontains=arg)
                    )

            if not len(people):
                self.stdout.write("No user found with that name or id \n")


            for person in people:
                            
                entries = timepiece.Entry.objects.filter(user=person, start_time__gte=start)
                
                if len(entries) or not all_flag: 
                    self.stdout.write("Checking " + person.first_name + ' ' + person.last_name + '...\n')
                
                for entry in entries:                   
                   if entry.is_overlapping(): 
                       output = str(person.first_name) + ' ' + str(person.last_name) + " with entry ID: " + str(entry.id) + ' from ' + str(entry.start_time) + ' to ' + str(entry.end_time) + ' on ' + str(entry.project) + '\n'
                       self.stdout.write(output)
                       
               
           
                 
