from django.db import models
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from datetime import datetime, date, timedelta
from pendulum.utils import determine_period

class PendulumConfiguration(models.Model):
    """
    This will hold a single record that maintains the configuration of the
    application.  In the admin interface, if the configuration is marked as
    "Is Monthly", that will take precedence over the "Install date" option (even
    if the install_date and period_length fields have values).  If you wish to
    use the fixed-length (install_date + period_length) setup, uncheck the
    is_monthly field.
    """

    # tie the configuration to one site in particular
    site = models.OneToOneField(Site, help_text="""Please choose the site that these settings will apply to.""")

    """
    this represents whether the application will look for all entries in a
    month-long period
    """
    is_monthly = models.BooleanField(default=True, help_text="""If you check this box, you will be forced to use the monthly mode.  Uncheck it to use fixed-length period""")

    """
    this is used in conjunction with the monthly setup; end date is assumed
    to be month_start - 1.  For example, if the periods begin on the 16th of
    each month, the end date would be assumed to be the 15th of each month
    """
    month_start = models.PositiveIntegerField(default=1, blank=True, null=True,
                                              help_text="""Enter 1 for periods that begin on the 1st day of each month and end on the last day of each month.  Alternatively, enter any other number (between 2 and 31) for the day of the month that periods start.  For example, enter 16 for periods that begin on the 16th of each month and end on the 15th of the following month.""")

    """
    install_date represents the date the software was installed and began
    being used.  period_length represents the number of days in a period.  Week-
    long periods would have a period_length of 7.  Two week-long periods would
    be 14 days.  You get the idea.  These should be able to handle _most_
    situations (maybe not all).
    """
    install_date = models.DateField(blank=True, null=True, help_text="""The date that Pendulum was installed.  Does not necessarily have to be the date, just a date to be used as a reference point for adding the number of days from period length below.  For example, if you have periods with a fixed length of 2 weeks, enter 14 days for period length and choose any Sunday to be the install date.""")
    period_length = models.PositiveIntegerField(blank=True, null=True, help_text="""The number of days in the fixed-length period.  For example, enter 7 days for 1-week periods or 28 for 4-week long periods.""")

    def __unicode__(self):
        return u'Pendulum Configuration for %s' % self.site

    def __current_mode(self):
        if self.is_monthly:
            return u'Month-long'
        else:
            return u'Fixed-length'
    current_mode = property(__current_mode)

class ProjectManager(models.Manager):
    """
    Return all active projects.
    """
    def get_query_set(self):
        return super(ProjectManager, self).get_query_set().filter(sites__exact=Site.objects.get_current())

    def active(self):
        return self.get_query_set().filter(is_active=True)

class Project(models.Model):
    """
    This class will keep track of different projects that one may clock into
    """

    name = models.CharField(max_length=100, unique=True,
                            help_text="""Please enter a name for this project.""")
    description = models.TextField(blank=True, null=True,
                                   help_text="""If necessary, enter something to describe the project.""")
    is_active = models.BooleanField(default=True,
                                    help_text="""Should this project be available for users to clock into?""")
    sites = models.ManyToManyField(Site, related_name='pendulum_projects',
                                  help_text="""Choose the site(s) that will display this project.""")
    date_added = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    objects = ProjectManager()

    def __unicode__(self):
        """
        The string representation of an instance of this class
        """
        return self.name

    def log_count(self):
        """
        Determine the number of entries associated with this project
        """
        return self.entries.all().count()

    def __total_hours(self):
        """
        Determine the number of hours spent working on each project
        """
        times = [e.total_hours for e in self.entries.all()]
        return '%.02f' % sum(times)
    total_hours = property(__total_hours)

    class Meta:
        ordering = ['name', 'date_added']

class ActivityManager(models.Manager):
    """
    Return all active activities.
    """
    def get_query_set(self):
        return super(ActivityManager, self).get_query_set().filter(sites__exact=Site.objects.get_current())

class Activity(models.Model):
    """
    Represents different types of activity: debugging, developing,
    brainstorming, QA, etc...
    """

    code = models.CharField(max_length=5, unique=True,
                            help_text="""Enter a short code to describe the type of activity that took place.""")
    name = models.CharField(max_length=50,
                            help_text="""Now enter a more meaningful name for the activity.""")
    sites = models.ManyToManyField(Site, related_name='pendulum_activities',
                                  help_text="""Choose the site(s) that will display this activity.""")

    objects = ActivityManager()

    def __unicode__(self):
        """
        The string representation of an instance of this class
        """
        return self.name

    def __log_count(self):
        """
        Determine the number of entries associated with this activity
        """
        return self.entries.all().count()
    log_count = property(__log_count)

    def __total_hours(self):
        """
        Determine the number of hours spent doing each type of activity
        """
        times = [e.total_hours for e in self.entries.all()]
        return '%.02f' % sum(times)
    total_hours = property(__total_hours)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'activities'

class EntryManager(models.Manager):
    #def get_query_set(self):
    #    return super(EntryManager, self).get_query_set().filter(site__exact=Site.objects.get_current())

    def current(self, user=None):
        """
        This will pull back any log entries for the current period.
        """
        try:
            set = self.in_period(determine_period())
        except PendulumConfiguration.DoesNotExist:
            raise Exception, "Please configure Pendulum!"
        else:
            if user:
                return set.filter(user=user)
            return set

    def previous(self, delta, user=None):
        set = self.in_period(determine_period(delta=delta))

        if user:
            return set.filter(user=user)
        return set

    def in_period(self, period, user=None):
        if not isinstance(period, tuple) or len(period) != 2:
            raise Exception('Invalid period specified')

        set = self.get_query_set().filter(start_time__range=period)

        if user:
            return set.filter(user=user)
        return set

class Entry(models.Model):
    """
    This class is where all of the time logs are taken care of
    """

    user = models.ForeignKey(User, related_name='pendulum_entries')
    project = models.ForeignKey(Project,
                                limit_choices_to={'is_active': True,
                                                  'sites': Site.objects.get_current()},
                                related_name='entries')
    activity = models.ForeignKey(Activity, blank=True, null=True, related_name='entries')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    seconds_paused = models.PositiveIntegerField(default=0)
    pause_time = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    date_updated = models.DateTimeField(auto_now=True)
    site = models.ForeignKey(Site, related_name='pendulum_entries')

    objects = EntryManager()

    def __total_hours(self):
        """
        Determine the total number of hours worked in this entry
        """
        if self.start_time and self.end_time:
            # only calculate when the start and end are defined
            delta = self.end_time - self.start_time
            seconds = delta.seconds - self.seconds_paused
        else:
            seconds = 0
            delta = timedelta(days=0)

        return seconds / 3600.0 + delta.days * 24
    total_hours = property(__total_hours)

    def __hours(self):
        """
        Print the hours in a nice, rounded format
        """
        return "%.02f" % self.total_hours
    hours = property(__hours)

    def __is_paused(self):
        """
        Determine whether or not this entry is paused
        """
        return self.pause_time != None
    is_paused = property(__is_paused)

    def pause(self):
        """
        If this entry is not paused, pause it.
        """
        if not self.is_paused:
            self.pause_time = datetime.now()

    def unpause(self):
        """
        If this entry is paused, unpause it
        """
        if self.is_paused:
            delta = datetime.now() - self.pause_time
            self.seconds_paused += delta.seconds
            self.pause_time = None

    def toggle_paused(self):
        """
        Toggle the paused state of this entry.  If the entry is already paused,
        it will be unpaused; if it is not paused, it will be paused.
        """
        if self.is_paused:
            self.unpause()
        else:
            self.pause()

    def __is_closed(self):
        """
        Determine whether this entry has been closed or not
        """
        return self.end_time != None
    is_closed = property(__is_closed)

    def clock_in(self, user, project):
        """
        Set this entry up for saving the first time, as an open entry.
        """
        if not self.is_closed:
            self.user = user
            self.project = project
            self.site = Site.objects.get_current()
            self.start_time = datetime.now()

    def clock_out(self, activity, comments):
        """
        Save some vital pieces of information about this entry upon closing
        """
        if self.is_paused:
            self.unpause()

        if not self.is_closed:
            self.end_time = datetime.now()
            self.activity = activity
            self.comments = comments

    def __delete_key(self):
        """
        Make it a little more interesting for deleting logs
        """
        salt = '%i-%i-apple-%s-sauce' % (self.id, self.is_paused, self.is_closed)
        try:
            import hashlib
        except ImportError:
            import sha
            key = sha.new(salt).hexdigest()
        else:
            key = hashlib.sha1(salt).hexdigest()
        return key
    delete_key = property(__delete_key)

    def __unicode__(self):
        """
        The string representation of an instance of this class
        """
        return '%s on %s' % (self.user, self.project)

    class Meta:
        ordering = ['-start_time']
        verbose_name_plural = 'entries'
        permissions = (
            ('can_clock_in', 'Can use Pendulum to clock in'),
            ('can_pause', 'Can pause and unpause log entries'),
            ('can_clock_out', 'Can use Pendulum to clock out'),
        )

# Add a utility method to the User class that will tell whether or not a
# particular user has any unclosed entries
User.clocked_in = property(lambda user: user.pendulum_entries.filter(end_time__isnull=True).count() > 0)
