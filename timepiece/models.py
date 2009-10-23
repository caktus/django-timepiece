import datetime
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.contrib.auth.models import User

from timepiece import utils

from dateutil.relativedelta import relativedelta

from crm import models as crm


class Project(models.Model):
    PROJECT_STATUSES = (
        ('requested', 'Requested'),
        ('accepted', 'Accepted'),
        ('finished', 'Finished'),
    )

    PROJECT_TYPES = (
        ('consultation', 'Consultation'),
        ('software', 'Software Project'),
    )

    name = models.CharField(max_length = 255)
    trac_environment = models.CharField(max_length = 255, blank=True, null=True)
    business = models.ForeignKey(
        crm.Contact, 
        related_name='business_projects', 
        limit_choices_to={'type': 'business'},
    )
    point_person = models.ForeignKey(User, limit_choices_to= {'is_staff':True})
    contacts = models.ManyToManyField(
        crm.Contact,
        related_name='contact_projects',
        through='ProjectRelationship',
    )

    type = models.CharField(max_length=15, choices=PROJECT_TYPES)
    status = models.CharField(max_length=15, choices=PROJECT_STATUSES)
    description = models.TextField()
    
    interactions = models.ManyToManyField(crm.Interaction)

    class Meta:
        ordering = ('name', 'status', 'type',)
        permissions = (
            ('view_project', 'Can view project'),
            ('email_project_report', 'Can email project report'),
        )

    def __unicode__(self):
        return self.name

    def trac_url(self):
        return settings.TRAC_URL % self.trac_environment
    
    def get_repeat_period(self):
        if not hasattr(self, '_repeat_period'):
            try:
                self._repeat_period = self.billing_periods.all()[0]
            except IndexError:
                self._repeat_period = None
        return self._repeat_period


class ProjectRelationship(models.Model):
    types = models.ManyToManyField(
        crm.RelationshipType,
        related_name='project_relationships',
        blank=True,
    )
    contact = models.ForeignKey(crm.Contact, limit_choices_to={'type': 'individual'})
    project = models.ForeignKey(Project)

    class Meta:
        unique_together = ('contact', 'project')

    def __unicode__(self):
        return "%s's relationship to %s" % (
            self.project.name,
            self.user.get_full_name(),
        )


class Activity(models.Model):
    """
    Represents different types of activity: debugging, developing,
    brainstorming, QA, etc...
    """
    code = models.CharField(
        max_length=5,
        unique=True,
        help_text="""Enter a short code to describe the type of activity that took place."""
    )
    name = models.CharField(
        max_length=50,
        help_text="""Now enter a more meaningful name for the activity.""",
    )

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'activities'


class Entry(models.Model):
    """
    This class is where all of the time logs are taken care of
    """

    user = models.ForeignKey(User, related_name='timepiece_entries')
    project = models.ForeignKey(Project, related_name='entries')
    activity = models.ForeignKey(
        Activity,
        blank=True,
        null=True,
        related_name='entries',
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    seconds_paused = models.PositiveIntegerField(default=0)
    pause_time = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    date_updated = models.DateTimeField(auto_now=True)
    hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    def save(self, force_insert=False, force_update=False):
        self.hours = Decimal('%.2f' % round(self.total_hours, 2))
        super(Entry, self).save()
    
    def get_seconds(self):
        """
        Determines the difference between the starting and ending time.  The
        result is returned as an integer of seconds.
        """
        if self.start_time and self.end_time:
            # only calculate when the start and end are defined
            delta = self.end_time - self.start_time
            seconds = delta.seconds - self.seconds_paused
        else:
            seconds = 0
            delta = datetime.timedelta(days=0)

        return seconds + (delta.days * 86400)

    def __total_hours(self):
        """
        Determined the total number of hours worked in this entry
        """
        return self.get_seconds() / 3600.0
    total_hours = property(__total_hours)
    
    def __is_paused(self):
        """
        Determine whether or not this entry is paused
        """
        return bool(self.pause_time)
    is_paused = property(__is_paused)
    
    def pause(self):
        """
        If this entry is not paused, pause it.
        """
        if not self.is_paused:
            self.pause_time = datetime.datetime.now()
    
    def unpause(self):
        """
        If this entry is paused, unpause it
        """
        if self.is_paused:
            delta = datetime.datetime.now() - self.pause_time
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
        return bool(self.end_time)
    is_closed = property(__is_closed)
    
    def clock_in(self, user, project):
        """
        Set this entry up for saving the first time, as an open entry.
        """
        if not self.is_closed:
            self.user = user
            self.project = project
            self.start_time = datetime.datetime.now()
    
    def clock_out(self, activity, comments):
        """
        Save some vital pieces of information about this entry upon closing
        """
        if self.is_paused:
            self.unpause()

        if not self.is_closed:
            self.end_time = datetime.datetime.now()
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
        verbose_name_plural = 'entries'
        permissions = (
            ('can_clock_in', 'Can use Pendulum to clock in'),
            ('can_pause', 'Can pause and unpause log entries'),
            ('can_clock_out', 'Can use Pendulum to clock out'),
        )

# Add a utility method to the User class that will tell whether or not a
# particular user has any unclosed entries
User.clocked_in = property(lambda user: user.timepiece_entries.filter(end_time__isnull=True).count() > 0)


class RepeatPeriod(models.Model):
    INTERVAL_CHOICES = (
        ('day', 'Day(s)'),
        ('week', 'Week(s)'),
        ('month', 'Month(s)'),
        ('year', 'Year(s)'),
    )
    project = models.ForeignKey(
        Project,
        unique=True,
        related_name='billing_periods',
    )
    count = models.PositiveSmallIntegerField(
        # null=True,
        # blank=True,
        choices=[(x,x) for x in range(1,32)],
    )
    interval = models.CharField(
        # null=True,
        # blank=True,
        max_length=10,
        choices=INTERVAL_CHOICES,
    )
    active = models.BooleanField(default=False)
    
    def __unicode__(self):
        return "%d %s for %s" % (self.count, self.get_interval_display(), self.project)
    
    def delta(self):
        return relativedelta(**{str(self.interval + 's'): self.count})
    
    def update_billing_windows(self):
        windows = []
        try:
            window = self.billing_windows.order_by('-date').select_related()[0]
        except IndexError:
            window = None
        if window:
            while window.date + self.delta() <= datetime.date.today():
                window.id = None
                window.date += self.delta()
                window.end_date += self.delta()
                window.save(force_insert=True)
                windows.append(window)
        else:
            window = self.billing_windows.create(
                date=datetime.date.today(),
                end_date=datetime.date.today() + self.delta(),
            )
            windows.append(window)
        return windows
    
    def get_window(self, window_id):
        try:
            window = self.billing_windows.select_related().get(pk=window_id)
        except BillingWindow.DoesNotExist:
            window = None
        return window
    
    def get_latest_window(self):
        try:
             window = self.billing_windows.select_related().latest()
        except BillingWindow.DoesNotExist:
            window = None
        if not window or window.date + window.period.delta() <= datetime.date.today():
            window = self.update_billing_windows()[-1]
        return window


class BillingWindow(models.Model):
    period = models.ForeignKey(RepeatPeriod, related_name='billing_windows')
    date = models.DateField()
    end_date = models.DateField()
    
    class Meta:
        get_latest_by = 'date'
    
    def __unicode__(self):
        return "%s through %s" % (self.date, self.end_date)
    
    def get_entries(self):
        if not hasattr(self, '_entries'):
            self._entries = Entry.objects.filter(
                project=self.period.project,
                start_time__gte=self.date,
                end_time__lt=self.end_date,
            ).select_related(
                'user',
            ).order_by('start_time')
        return self._entries
    
    def total_hours(self):
        return Entry.objects.filter(
            project=self.period.project,
            start_time__gte=self.date,
            end_time__lt=self.end_date,
        ).aggregate(hours=models.Sum('hours'))['hours']
    
    def next(self):
        if not hasattr(self, '_next'):
            try:
                window = BillingWindow.objects.filter(
                    period=self.period,
                    date__gt=self.date,
                ).order_by('date')[0]
            except IndexError:
                window = None
            self._next = window
        return self._next
    
    def previous(self):
        if not hasattr(self, '_previous'):
            try:
                window = BillingWindow.objects.filter(
                    period=self.period,
                    date__lt=self.date,
                ).order_by('-date')[0]
            except IndexError:
                window = None
            self._previous = window
        return self._previous
