import datetime
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q, Avg, Sum, Max, Min
from django.contrib.auth.models import User

from timepiece import utils

from dateutil.relativedelta import relativedelta

from datetime import timedelta

from crm import models as crm

try:
    settings.TIMEPIECE_TIMESHEET_EDITABLE_DAYS
except AttributeError:
    settings.TIMEPIECE_TIMESHEET_EDITABLE_DAYS = 3

class Attribute(models.Model):
    ATTRIBUTE_TYPES = (
        ('project-type', 'Project Type'),
        ('project-status', 'Project Status'),
    )
    SORT_ORDER_CHOICES = [(x,x) for x in xrange(-20,21)]
    type = models.CharField(max_length=32, choices=ATTRIBUTE_TYPES)
    label = models.CharField(max_length=255)
    sort_order = models.SmallIntegerField(
        null=True, 
        blank=True, 
        choices=SORT_ORDER_CHOICES,
    )
    enable_timetracking = models.BooleanField('Enables time tracking '
        'functionality for projects with this type or status.',
        default=False,
    )
    
    class Meta:
        unique_together = ('type', 'label')
        ordering = ('sort_order',)
    
    def __unicode__(self):
        return self.label


class Project(models.Model):
    name = models.CharField(max_length = 255)
    trac_environment = models.CharField(max_length=255, blank=True, null=True)
    business = models.ForeignKey(
        crm.Contact, 
        related_name='business_projects', 
        limit_choices_to={'type': 'business'},
    )
    point_person = models.ForeignKey(User, limit_choices_to={'is_staff': True})
    contacts = models.ManyToManyField(
        crm.Contact,
        related_name='contact_projects',
        through='ProjectRelationship',
    )
    type = models.ForeignKey(
        Attribute, 
        limit_choices_to={'type': 'project-type'},
        related_name='projects_with_type',
    )
    status = models.ForeignKey(
        Attribute, 
        limit_choices_to={'type': 'project-status'},
        related_name='projects_with_status',
    )
    description = models.TextField()
    
    interactions = models.ManyToManyField(crm.Interaction, blank=True)
    
    billing_period = models.ForeignKey(
        'RepeatPeriod',
        null=True,
        blank=True,
        related_name='projects',
    )
    
    class Meta:
        ordering = ('name', 'status', 'type',)
        permissions = (
            ('view_project', 'Can view project'),
            ('email_project_report', 'Can email project report'),
            ('view_project_time_sheet', 'Can view project time sheet'),
            ('export_project_time_sheet', 'Can export project time sheet'),
        )

    def __unicode__(self):
        return self.name

    def trac_url(self):
        return settings.TRAC_URL % self.trac_environment


class ProjectRelationship(models.Model):
    types = models.ManyToManyField(
        crm.RelationshipType,
        related_name='project_relationships',
        blank=True,
    )
    contact = models.ForeignKey(
        crm.Contact,
        limit_choices_to={'type': 'individual'},
        related_name='project_relationships',
    )
    project = models.ForeignKey(
        Project,
        related_name='project_relationships',
    )

    class Meta:
        unique_together = ('contact', 'project')

    def __unicode__(self):
        return "%s's relationship to %s" % (
            self.project.name,
            self.contact.get_full_name(),
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


class Location(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.CharField(max_length=255, unique=True)
    
    def __unicode__(self):
        return self.name


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
    location = models.ForeignKey(
        Location,
        related_name='entries',
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    seconds_paused = models.PositiveIntegerField(default=0)
    pause_time = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True)
    date_updated = models.DateTimeField(auto_now=True)
    hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    billable = models.BooleanField(default=True)

    def is_overlapping(self):
        if self.start_time and self.end_time:
            entries = self.user.timepiece_entries.filter(
            Q(end_time__range=(self.start_time,self.end_time))|\
            Q(start_time__range=(self.start_time,self.end_time))|\
            Q(start_time__lte=self.start_time, end_time__gte=self.end_time))
            totals = entries.aggregate(
            max=Max('end_time'),min=Min('start_time'))
            totals['total'] = 0
            for entry in entries:
                totals['total'] = totals['total'] + entry.get_seconds()
            totals['diff'] = totals['max']-totals['min']
            totals['diff'] = totals['diff'].seconds + totals['diff'].days*86400
            if totals['total'] > totals['diff']:
                return True
            else:
                return False
        else:
            return None
    
    def save(self, **kwargs):
        self.hours = Decimal('%.2f' % round(self.total_hours, 2))
        super(Entry, self).save(**kwargs)
    
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
    
    def pause_all(self):
        """
        Pause all open entries
        """
        entries = self.user.timepiece_entries.filter(
        end_time__isnull=True).all()
        for entry in entries:
            entry.pause()
            entry.save()
    
    def unpause(self, date=None):
        if self.is_paused:
            self.pause_all()
            if not date:
                date = datetime.datetime.now()
            delta = date - self.pause_time
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
            self.pause_all()
            if not self.start_time:
                self.start_time = datetime.datetime.now()
    
    def __billing_window(self):
        return BillingWindow.objects.get(
            period__contacts__user=self.user,
            date__lte = self.end_time,
            end_date__gt = self.end_time)
    billing_window = property(__billing_window)
    
    def __is_editable(self):
        if self.end_time:
            try:
                end_date =self.billing_window.end_date+\
                    timedelta(days=settings.TIMEPIECE_TIMESHEET_EDITABLE_DAYS)
                return end_date >= datetime.date.today()
            except:
                return True
        else:
            return True
    is_editable = property(__is_editable)
        
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
            ('view_entry_summary', 'Can view entry summary page'),
        )

# Add a utility method to the User class that will tell whether or not a
# particular user has any unclosed entries
User.clocked_in = property(lambda user: user.timepiece_entries.filter(end_time__isnull=True).count() > 0)


class RepeatPeriodManager(models.Manager):
    def update_billing_windows(self, date_boundary=None):
        active_billing_periods = self.filter(
            active=True,
        ).select_related(
            'project'
        )
        windows = []
        for period in active_billing_periods:
            windows += ((period, period.update_billing_windows(date_boundary)),)
        return windows


class RepeatPeriod(models.Model):
    INTERVAL_CHOICES = (
        ('day', 'Day(s)'),
        ('week', 'Week(s)'),
        ('month', 'Month(s)'),
        ('year', 'Year(s)'),
    )
    count = models.PositiveSmallIntegerField(
        choices=[(x,x) for x in range(1,32)],
    )
    interval = models.CharField(
        max_length=10,
        choices=INTERVAL_CHOICES,
    )
    active = models.BooleanField(default=False)
    
    contacts = models.ManyToManyField(
        crm.Contact,
        blank=True,
        through='PersonRepeatPeriod',
        related_name='repeat_periods',
    )
    
    objects = RepeatPeriodManager()
    
    def __unicode__(self):
        return "%d %s" % (self.count, self.get_interval_display())
    
    def delta(self):
        return relativedelta(**{str(self.interval + 's'): self.count})
    
    def update_billing_windows(self, date_boundary=None):
        if not date_boundary:
            date_boundary = datetime.date.today()
        windows = []
        try:
            window = self.billing_windows.order_by('-date').select_related()[0]
        except IndexError:
            window = None
        if window:
            start_date = window.date
            while window.date + self.delta() <= date_boundary:
                window.id = None
                if window.date + self.delta() == window.end_date:
                    # same delta as last time
                    window.date += self.delta()
                else:
                    # delta changed, make sure to include extra time
                    window.date = window.end_date
                window.end_date += self.delta()
                window.save(force_insert=True)
            return self.billing_windows.filter(
                date__gt=start_date
            ).order_by('date')
        else:
            return []

class BillingWindow(models.Model):
    period = models.ForeignKey(RepeatPeriod, related_name='billing_windows')
    date = models.DateField()
    end_date = models.DateField()
    
    class Meta:
        get_latest_by = 'date'
    
    def __unicode__(self):
        return "%s through %s" % (self.date, self.end_date)
    
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

    def __entries(self):
            return Entry.objects.filter(
                end_time__lte = self.end_date,
                end_time__gt = self.date)
    entries = property(__entries)
    
class PersonRepeatPeriod(models.Model):
    contact = models.ForeignKey(
        crm.Contact,
        unique=True,
        limit_choices_to={'type': 'individual'}
    )
    repeat_period = models.ForeignKey(
        RepeatPeriod,
        unique=True,
    )
    
    def summary(self, date, end_date):
        projects = getattr(settings, 'TIMEPIECE_PROJECTS', {})
        user = self.contact.user
        entries = user.timepiece_entries.filter(end_time__gt=date,
                                                end_time__lte=end_date)
        data = {}
        data['total'] = entries.aggregate(s=Sum('hours'))['s']
        billable = entries.exclude(project__in=projects.values())
        billable = billable.values('billable').annotate(s=Sum('hours'))
        for row in billable:
            if row['billable']:
                data['billable'] = row['s']
            else:
                data['non_billable'] = row['s']
        vacation = entries.filter(project=projects['vacation'])
        data['vacation'] = vacation.aggregate(s=Sum('hours'))['s']
        sick = entries.filter(project=projects['sick'])
        data['sick'] = sick.aggregate(s=Sum('hours'))['s']
        return data

    def list_total_hours(self, N = 2):
        bw = BillingWindow.objects.filter(period=self.repeat_period).order_by('-date')[:N]
        result = []
        for b in bw:
            result.append(self.contact.user.timepiece_entries.filter(
                end_time__lte = b.end_date,
                end_time__gt = b.date
            ).aggregate(total=Sum('hours')))
        return result


class ProjectContract(models.Model):
    CONTRACT_STATUS = (
        ('upcoming', 'Upcoming'),
        ('current', 'Current'),
        ('complete', 'Complete'),
    )

    project = models.ForeignKey(Project, related_name='contracts')
    start_date = models.DateField()
    end_date = models.DateField()
    num_hours = models.DecimalField(max_digits=8, decimal_places=2,
                                    default=0)
    status = models.CharField(choices=CONTRACT_STATUS, default='upcomming',
                              max_length=32)

    def hours_worked(self):
        # TODO put this in a .extra w/a subselect
        if not hasattr(self, '_hours_worked'):
            self._hours_worked = Entry.objects.filter(
                project=self.project,
                start_time__gte=self.start_date,
                end_time__lt=self.end_date + datetime.timedelta(days=1),
            ).aggregate(sum=Sum('hours'))['sum']
        return self._hours_worked or 0

    @property
    def hours_assigned(self):
        # TODO put this in a .extra w/a subselect
        if not hasattr(self, '_hours_assigned'):
            self._hours_assigned =\
              self.assignments.aggregate(sum=Sum('num_hours'))['sum']
        return self._hours_assigned or 0

    def __unicode__(self):
        return unicode(self.project)


class ContractAssignment(models.Model):
    contract = models.ForeignKey(ProjectContract, related_name='assignments')
    contact = models.ForeignKey(
        crm.Contact,
        limit_choices_to={'type': 'individual'},
        related_name='assignments',
    )
    start_date = models.DateField()
    end_date = models.DateField()
    num_hours = models.DecimalField(max_digits=8, decimal_places=2,
                                    default=0)

    @property
    def hours_worked(self):
        # TODO (maybe) put this in a .extra w/a subselect
        if not hasattr(self, '_hours_worked'):
            self._hours_worked = Entry.objects.filter(
                user=self.contact.user,
                project=self.contract.project,
                start_time__gte=self.start_date,
                end_time__lt=self.end_date + datetime.timedelta(days=1),
            ).aggregate(sum=Sum('hours'))['sum']
        return self._hours_worked or 0

    @property
    def hours_remaining(self):
        return self.num_hours - self.hours_worked

    class Meta:
        unique_together = (('contract', 'contact'),)

    def __unicode__(self):
        return u'%s / %s' % (self.contact, self.contract.project)


class PersonSchedule(models.Model):
    contact = models.ForeignKey(
        crm.Contact,
        unique=True,
        limit_choices_to={'type': 'individual'}
    )
    hours_per_week = models.DecimalField(max_digits=8, decimal_places=2,
                                         default=0)
    end_date = models.DateField()

    @property
    def hours_available(self):
        today = datetime.date.today()
        weeks_remaining = (self.end_date - today).days/7.0
        return float(self.hours_per_week) * weeks_remaining

    @property
    def hours_scheduled(self):
        if not hasattr(self, '_hours_scheduled'):
            self._hours_scheduled = 0
            now = datetime.datetime.now()
            for assignment in self.contact.assignments.filter(end_date__gte=now):
                self._hours_scheduled += assignment.hours_remaining
        return self._hours_scheduled

    def __unicode__(self):
        return unicode(self.contact)
