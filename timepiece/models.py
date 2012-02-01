import datetime
import logging
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q, Avg, Sum, Max, Min
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS

from timepiece import utils

from dateutil.relativedelta import relativedelta
from dateutil import rrule

from datetime import timedelta


class Attribute(models.Model):
    ATTRIBUTE_TYPES = (
        ('project-type', 'Project Type'),
        ('project-status', 'Project Status'),
    )
    SORT_ORDER_CHOICES = [(x, x) for x in xrange(-20, 21)]
    type = models.CharField(max_length=32, choices=ATTRIBUTE_TYPES)
    label = models.CharField(max_length=255)
    sort_order = models.SmallIntegerField(
        null=True,
        blank=True,
        choices=SORT_ORDER_CHOICES,
    )
    enable_timetracking = models.BooleanField(default=False,
        help_text='Enable time tracking functionality for projects with this '
                  'type or status.',
    )
    billable = models.BooleanField(default=False)

    class Meta:
        unique_together = ('type', 'label')
        ordering = ('sort_order',)

    def __unicode__(self):
        return self.label


class Business(models.Model):
    name = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    external_id = models.CharField(max_length=32, blank=True)

    def save(self, *args, **kwargs):
        queryset = Business.objects.all()
        if not self.slug:
            if self.id:
                queryset = queryset.exclude(id__exact=self.id)
            self.slug = utils.slugify_uniquely(self.name, queryset, 'slug')
        super(Business, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)


class Project(models.Model):
    name = models.CharField(max_length=255)
    trac_environment = models.CharField(max_length=255, blank=True, null=True)
    business = models.ForeignKey(
        Business,
        related_name='new_business_projects',
    )
    point_person = models.ForeignKey(User, limit_choices_to={'is_staff': True})
    users = models.ManyToManyField(
        User,
        related_name='user_projects',
        through='ProjectRelationship',
    )
    activity_group = models.ForeignKey(
        'ActivityGroup',
        related_name='activity_group',
        null=True,
        blank=True,
        verbose_name="restrict activities to",
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


class RelationshipType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.CharField(max_length=255, unique=True, editable=False)

    def save(self):
        queryset = RelationshipType.objects.all()
        if self.id:
            queryset = queryset.exclude(id__exact=self.id)
        self.slug = utils.slugify_uniquely(self.name, queryset, 'slug')
        super(RelationshipType, self).save()

    def __unicode__(self):
        return self.name


class ProjectRelationship(models.Model):
    types = models.ManyToManyField(
        RelationshipType,
        related_name='project_relationships',
        blank=True,
    )
    user = models.ForeignKey(
        User,
        related_name='project_relationships',
    )
    project = models.ForeignKey(
        Project,
        related_name='project_relationships',
    )

    class Meta:
        unique_together = ('user', 'project')

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
        help_text='Enter a short code to describe the type of ' + \
            'activity that took place.'
    )
    name = models.CharField(
        max_length=50,
        help_text="""Now enter a more meaningful name for the activity.""",
    )
    billable = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'activities'


class HourGroup(models.Model):
    """Activities that are bundled together for billing"""

    name = models.CharField(max_length=255, unique=True)
    activities = models.ManyToManyField(
        Activity,
        related_name='activity_bundle',
    )
    order = models.PositiveIntegerField(unique=True, blank=True, null=True)

    def __unicode__(self):
        return self.name


class ActivityGroup(models.Model):
    """Activities that are allowed for a project"""

    name = models.CharField(max_length=255, unique=True)
    activities = models.ManyToManyField(
        Activity,
        related_name='activity_group',
    )

    def __unicode__(self):
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return self.name


ENTRY_STATUS = (
    ('unverified', 'Unverified',),
    ('verified', 'Verified',),
    ('approved', 'Approved',),
    ('invoiced', 'Invoiced',),
    ('not-invoiced', 'Not Invoiced',),
)


class EntryManager(models.Manager):
    def get_query_set(self):
        qs = super(EntryManager, self).get_query_set()
        qs = qs.select_related('activity', 'project__type')
        # ensure our select_related are added.  Without this line later calls
        # to select_related will void ours (not sure why - probably a bug
        # in Django)
        foo = str(qs.query)
        qs = qs.extra({'billable': 'timepiece_activity.billable AND '
                                   'timepiece_attribute.billable'})
        return qs

    def date_trunc(self, key='month'):
        qs = self.get_query_set()
        select = {"day": {"date": """DATE_TRUNC('day', end_time)"""},
                  "week": {"date": """DATE_TRUNC('week', end_time)"""},
                  "month": {"date": """DATE_TRUNC('month', end_time)"""},
        }
        qs = qs.extra(select=select[key]).values('user', 'user__first_name',
                                                 'user__last_name', 'date',
                                                 'billable',)
        qs = qs.annotate(hours=Sum('hours')).order_by('user__last_name',
                                                      'date')
        return qs


class EntryWorkedManager(models.Manager):
    def get_query_set(self):
        qs = super(EntryWorkedManager, self).get_query_set()
        projects = getattr(settings, 'TIMEPIECE_PROJECTS', {})
        return qs.exclude(project__in=projects.values())


class Entry(models.Model):
    """
    This class is where all of the time logs are taken care of
    """

    user = models.ForeignKey(User, related_name='timepiece_entries')
    project = models.ForeignKey(Project, related_name='entries')
    activity = models.ForeignKey(
        Activity,
        related_name='entries',
    )
    location = models.ForeignKey(
        Location,
        related_name='entries',
    )
    entry_group = models.ForeignKey(
       'EntryGroup',
        related_name='entries',
        blank=True, null=True,
        on_delete=models.SET_NULL,
    )
    status = models.CharField(
        max_length=24,
        choices=ENTRY_STATUS,
        default='unverified',
    )

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    seconds_paused = models.PositiveIntegerField(default=0)
    pause_time = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True)
    date_updated = models.DateTimeField(auto_now=True)

    hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    objects = EntryManager()
    worked = EntryWorkedManager()

    def check_overlap(self, entry_b, **kwargs):
        """
        Given two entries, return True if they overlap, otherwise return False
        """
        consider_pause = kwargs.get('pause', True)
        entry_a = self
        #if entries are open, consider them to be closed right now
        if not entry_a.end_time or not entry_b.end_time:
            return False
        #Check the two entries against each other
        start_inside = entry_a.start_time > entry_b.start_time \
            and entry_a.start_time < entry_b.end_time
        end_inside = entry_a.end_time > entry_b.start_time \
            and entry_a.end_time < entry_b.end_time
        a_is_inside = entry_a.start_time > entry_b.start_time \
            and entry_a.end_time < entry_b.end_time
        b_is_inside = entry_a.start_time < entry_b.start_time \
            and entry_a.end_time > entry_b.end_time
        overlap = start_inside or end_inside or a_is_inside or b_is_inside
        if not consider_pause:
            return overlap
        else:
            if overlap:
                max_end = max(entry_a.end_time, entry_b.end_time)
                min_start = min(entry_a.start_time, entry_b.start_time)
                diff = max_end - min_start
                diff = diff.seconds + diff.days * 86400
                total = entry_a.get_seconds() + entry_b.get_seconds() - 1
                if total >= diff:
                    return True
            return False

    def is_overlapping(self):
        if self.start_time and self.end_time:
            entries = self.user.timepiece_entries.filter(
            Q(end_time__range=(self.start_time, self.end_time)) | \
            Q(start_time__range=(self.start_time, self.end_time)) | \
            Q(start_time__lte=self.start_time, end_time__gte=self.end_time))

            totals = entries.aggregate(
            max=Max('end_time'), min=Min('start_time'))

            totals['total'] = 0
            for entry in entries:
                totals['total'] = totals['total'] + entry.get_seconds()

            totals['diff'] = totals['max'] - totals['min']
            totals['diff'] = totals['diff'].seconds + \
                totals['diff'].days * 86400

            if totals['total'] > totals['diff']:
                return True
            else:
                return False
        else:
            return None

    def clean(self):
        if not self.user_id:
            raise ValidationError('An unexpected error has occured')
        if not self.start_time:
            raise ValidationError('Please enter a valid start time')
        start = self.start_time
        if self.end_time:
            end = self.end_time
        #Current entries have no end_time
        else:
            end = start + datetime.timedelta(seconds=1)
        entries = self.user.timepiece_entries.filter(
            Q(end_time__range=(start, end)) | \
            Q(start_time__range=(start, end)) | \
            Q(start_time__lte=start, end_time__gte=end))
        #An entry can not conflict with itself so remove it from the list
        if self.id:
            entries = entries.exclude(pk=self.id)
        for entry in entries:
            entry_data = {
                'project': entry.project,
                'activity': entry.activity,
                'start_time': entry.start_time,
                'end_time': entry.end_time
            }
            #Conflicting saved entries
            if entry.end_time:
                if entry.start_time.date() == start.date() \
                and entry.end_time.date() == end.date():
                    entry_data['start_time'] = entry.start_time.strftime(
                        '%H:%M:%S')
                    entry_data['end_time'] = entry.end_time.strftime(
                        '%H:%M:%S')
                    output = 'Start time overlaps with: ' + \
                    '%(project)s - %(activity)s - ' % entry_data + \
                    'from %(start_time)s to %(end_time)s' % entry_data
                    raise ValidationError(output)
                else:
                    entry_data['start_time'] = entry.start_time.strftime(
                        '%H:%M:%S on %m\%d\%Y')
                    entry_data['end_time'] = entry.end_time.strftime(
                        '%H:%M:%S on %m\%d\%Y')
                    output = 'Start time overlaps with: ' + \
                    '%(project)s - %(activity)s - ' % entry_data + \
                    'from %(start_time)s to %(end_time)s' % entry_data
                    raise ValidationError(output)
        try:
            activity_group = self.project.activity_group
            if activity_group:
                activity = self.activity
                if not activity_group.activities.filter(pk=activity.pk).exists():
                    name = activity.name
                    err_msg = '%s is not allowed for this project. ' % name
                    allowed = activity_group.activities.filter()
                    allowed = allowed.values_list('name', flat=True)
                    allowed_names = ['among ']
                    if len(allowed) > 1:
                        for index, activity in enumerate(allowed):
                            allowed_names += activity
                            if index < len(allowed) - 2:
                                allowed_names += ', '
                            elif index < len(allowed) - 1:
                                allowed_names += ', and '
                        allowed_activities = ''.join(allowed_names)
                    else:
                        allowed_activities = allowed[0]
                    err_msg += 'Please choose %s' % allowed_activities
                    raise ValidationError(err_msg)
        except (Project.DoesNotExist, Activity.DoesNotExist):
            # Will be caught by field requirements
            pass
        if end <= start:
            raise ValidationError('Ending time must exceed the starting time')
        return True

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
        total = self.get_seconds() / 3600.0
        #in case seconds paused are greater than the elapsed time
        if total < 0:
            total = 0
        return total
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
            if not self.start_time:
                self.start_time = datetime.datetime.now()

    def __billing_window(self):
        return BillingWindow.objects.get(
            period__users=self.user,
            date__lte=self.end_time,
            end_date__gt=self.end_time)
    billing_window = property(__billing_window)

    def __is_editable(self):
        return self.status == 'unverified'
    is_editable = property(__is_editable)

    def __delete_key(self):
        """
        Make it a little more interesting for deleting logs
        """
        salt = '%i-%i-apple-%s-sauce' \
            % (self.id, self.is_paused, self.is_closed)
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


class EntryGroup(models.Model):
    VALID_STATUS = ('invoiced', 'not-invoiced')
    STATUS_CHOICES = [status for status in ENTRY_STATUS \
                      if status[0] in VALID_STATUS]
    user = models.ForeignKey(User, related_name='entry_group')
    project = models.ForeignKey(Project, related_name='entry_group')
    status = models.CharField(max_length=24, choices=STATUS_CHOICES,
                              default='invoiced')
    number = models.IntegerField("Reference #", blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    start = models.DateField(blank=True, null=True)
    end = models.DateField()

    def delete(self):
        self.entries.update(status='approved')
        super(EntryGroup, self).delete()

    def __unicode__(self):
        invoice_data = {
            'number': self.number,
            'status': self.status,
            'project': self.project,
            'end': self.end.strftime('%b %Y'),
        }
        return 'Entry Group ' + \
               '%(number)s: %(status)s - %(project)s - %(end)s' % invoice_data


# Add a utility method to the User class that will tell whether or not a
# particular user has any unclosed entries
User.clocked_in = property(lambda user: user.timepiece_entries.filter(
    end_time__isnull=True).count() > 0)


class RepeatPeriodManager(models.Manager):
    def update_billing_windows(self, date_boundary=None):
        active_billing_periods = self.filter(
            active=True,
        ).select_related(
            'project'
        )
        windows = []
        for period in active_billing_periods:
            windows += ((period,
                period.update_billing_windows(date_boundary)),)
        return windows


class RepeatPeriod(models.Model):
    INTERVAL_CHOICES = (
        ('day', 'Day(s)'),
        ('week', 'Week(s)'),
        ('month', 'Month(s)'),
        ('year', 'Year(s)'),
    )
    count = models.PositiveSmallIntegerField(
        choices=[(x, x) for x in range(1, 32)],
    )
    interval = models.CharField(
        max_length=10,
        choices=INTERVAL_CHOICES,
    )
    active = models.BooleanField(default=False)

    users = models.ManyToManyField(
        User,
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
                end_time__lte=self.end_date,
                end_time__gt=self.date)
    entries = property(__entries)


class PersonRepeatPeriod(models.Model):
    user = models.ForeignKey(
        User,
        unique=True,
        null=True,
    )
    repeat_period = models.ForeignKey(
        RepeatPeriod,
        unique=True,
    )

    def hours_in_week(self, date):
        left, right = utils.get_week_window(date)
        entries = Entry.worked.filter(user=self.user)
        entries = entries.filter(
            (Q(status='invoiced') | Q(status='approved')),
            end_time__gt=left, end_time__lt=right,)
        return entries.aggregate(s=Sum('hours'))['s']

    def overtime_hours_in_week(self, date):
        hours = self.hours_in_week(date)
        if hours > 40:
            return hours - 40
        return 0

    def total_monthly_overtime(self, day):
        start = day.replace(day=1)
        weeks = utils.generate_dates(start=start,
                                     end=utils.get_last_billable_day(start))
        overtime = Decimal('0.0')
        for week in weeks:
            overtime += self.overtime_hours_in_week(week)
        return overtime

    def summary(self, date, end_date, verified=True):
        """
        Returns a summary of hours worked in the given time frame, for this
        user.  The setting TIMEPIECE_PROJECTS can be used to separate out hours
        for paid leave that should not be included in the total worked (e.g.,
        sick time, vacation time, etc.).  Those hours will be added to the
        summary separately using the dictionary key set in TIMEPIECE_PROJECTS.
        """
        projects = getattr(settings, 'TIMEPIECE_PROJECTS', {})
        user = self.user
        entries = user.timepiece_entries.filter(
            end_time__gt=date, end_time__lt=end_date)
        if verified:
            entries = entries.filter(Q(status='invoiced') | \
                                     Q(status='approved'))
        data = {
            'billable': Decimal('0'), 'non_billable': Decimal('0'),
            'invoiced': Decimal('0'), 'uninvoiced': Decimal('0'),
            'total': Decimal('0')
            }
        invoiced = entries.filter(
            status='invoiced').aggregate(i=Sum('hours'))['i']
        uninvoiced = entries.exclude(
            status='invoiced').aggregate(uninv=Sum('hours'))['uninv']
        total = entries.aggregate(s=Sum('hours'))['s']
        if invoiced:
            data['invoiced'] = invoiced
        if uninvoiced:
            data['uninvoiced'] = uninvoiced
        if total:
            data['total'] = total
        billable = entries.exclude(project__in=projects.values())
        billable = billable.values(
            'billable',
        ).annotate(s=Sum('hours'))
        for row in billable:
            if row['billable']:
                data['billable'] += row['s']
            else:
                data['non_billable'] += row['s']
        data['total_worked'] = data['billable'] + data['non_billable']
        data['paid_leave'] = {}
        for name, pk in projects.iteritems():
            qs = entries.filter(project=projects[name])
            data['paid_leave'][name] = qs.aggregate(s=Sum('hours'))['s']
        return data

    def list_total_hours(self, N=2):
        bw = BillingWindow.objects.filter(period=self.repeat_period).order_by(
            '-date')[:N]
        result = []
        for b in bw:
            result.append(self.user.timepiece_entries.filter(
                end_time__lte=b.end_date,
                end_time__gt=b.date
            ).aggregate(total=Sum('hours')))
        return result

    class Meta:
        permissions = (
            ('view_person_time_sheet', 'Can view person\'s timesheet.'),
            ('edit_person_time_sheet', 'Can edit person\'s timesheet.'),
        )


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

    @property
    def hours_allocated(self):
        allocations = AssignmentAllocation.objects.filter(
            assignment__contract=self)
        return allocations.aggregate(sum=Sum('hours'))['sum']

    @property
    def hours_remaining(self):
        return self.num_hours - self.hours_worked()

    @property
    def weeks_remaining(self):
        return utils.generate_dates(end=self.end_date, by='week')

    def __unicode__(self):
        return unicode(self.project)


class ContractMilestone(models.Model):
    contract = models.ForeignKey(ProjectContract, related_name='milestones')
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    hours = models.DecimalField(max_digits=8, decimal_places=2,
                                default=0)

    class Meta(object):
        ordering = ('end_date',)

    def hours_worked(self):
        """Hours worked during this milestone"""
        if not hasattr(self, '_hours_worked'):
            self._hours_worked = Entry.objects.filter(
                project=self.contract.project,
                start_time__gte=self.start_date,
                end_time__lt=self.end_date + datetime.timedelta(days=1),
            ).aggregate(sum=Sum('hours'))['sum']
        return self._hours_worked or 0

    def total_budget(self):
        """Total budget through the end of this milestone"""
        if not hasattr(self, '_total_budget'):
            end_date = self.end_date + datetime.timedelta(days=1)
            previous = self.contract.milestones.filter(end_date__lt=end_date)
            self._total_budget = previous.aggregate(sum=Sum('hours'))['sum']
        return self._total_budget or 0

    def total_hours_worked(self):
        """Total hours worked on project through the end of this milestone"""
        if not hasattr(self, '_total_hours_worked'):
            self._total_hours_worked = Entry.objects.filter(
                project=self.contract.project,
                start_time__gte=self.contract.start_date,
                end_time__lt=self.end_date + datetime.timedelta(days=1),
            ).aggregate(sum=Sum('hours'))['sum']
        return self._total_hours_worked or 0

    def hours_remaining(self):
        """Hours over the milestone budget"""
        return self.hours - self.hours_worked()

    def total_hours_remaining(self):
        """Hours over the entire project budget"""
        return self.total_budget() - self.total_hours_worked()

    def is_before(self):
        return self.start_date > datetime.date.today()

    def is_complete(self):
        return self.end_date < datetime.date.today()


class AssignmentManager(models.Manager):
    def active_during_week(self, week, next_week):
        q = Q(contract__end_date__gte=week, contract__end_date__lt=next_week)
        q |= Q(contract__start_date__gte=week,
            contract__start_date__lt=next_week)
        q |= Q(contract__start_date__lt=week, contract__end_date__gt=next_week)
        return self.get_query_set().filter(q)

    def sort_by_priority(self):
        return sorted(self.get_query_set().all(),
            key=lambda contract: contract.this_weeks_priority_number)


# contract assignment logger
logger = logging.getLogger('timepiece.ca')


class ContractAssignment(models.Model):
    contract = models.ForeignKey(ProjectContract, related_name='assignments')
    user = models.ForeignKey(
        User,
        related_name='assignments',
    )
    start_date = models.DateField()
    end_date = models.DateField()
    num_hours = models.DecimalField(max_digits=8, decimal_places=2,
                                    default=0)
    min_hours_per_week = models.IntegerField(default=0)

    objects = AssignmentManager()

    def _log(self, msg):
        logger.debug('{0} - {1}'.format(self, msg))

    def _filtered_hours_worked(self, end_date):
        return Entry.objects.filter(
            user=self.user,
            project=self.contract.project,
            start_time__gte=self.start_date,
            end_time__lt=end_date,
        ).aggregate(sum=Sum('hours'))['sum'] or 0

    def filtered_hours_worked_with_in_window(self, start_date, end_date):
        return Entry.objects.filter(
            user=self.user,
            project=self.contract.project,
            start_time__gte=start_date,
            end_time__lt=end_date,
        ).aggregate(sum=Sum('hours'))['sum'] or 0

    @property
    def hours_worked(self):
        if not hasattr(self, '_hours_worked'):
            date = self.end_date + datetime.timedelta(days=1)
            self._hours_worked = self._filtered_hours_worked(date)
        return self._hours_worked or 0

    @property
    def hours_remaining(self):
        return self.num_hours - self.hours_worked

    @property
    def this_weeks_priority_number(self):
        """
        Only works if already filtered to the current week. Otherwise groups
        outside the range will be listed as ongoing instead of befor or after.
        """
        if not hasattr(self, '_priority_type'):
            weeks = utils.get_week_window(datetime.datetime.now())
            if self.end_date < weeks[1].date() \
            and self.end_date >= weeks[0].date():
                self._priority_type = 0
            elif self.start_date < weeks[1].date() \
            and self.start_date >= weeks[0].date():
                self._priority_type = 1
            else:
                self._priority_type = 2
        return self._priority_type

    @property
    def this_weeks_priority_type(self):
        type_list = ['ending', 'starting', 'ongoing', ]
        return type_list[self.this_weeks_priority_number]

    def get_average_weekly_committment(self):
        week_start = utils.get_week_start()
        # calculate hours left on contract (subtract worked hours this week)
        remaining = self.num_hours - self._filtered_hours_worked(week_start)
        commitment = remaining / self.contract.weeks_remaining.count()
        return commitment

    def weekly_commitment(self, day=None):
        self._log("Commitment for {0}".format(day))
        # earlier assignments may have already allocated time for this week
        unallocated = self.unallocated_hours_for_week(day)
        self._log('Unallocated hours {0}'.format(unallocated))
        reserved = self.remaining_min_hours()
        self._log('Reserved hours {0}'.format(reserved))
        # start with unallocated hours
        commitment = unallocated
        # reserve required hours on later assignments (min_hours_per_week)
        commitment -= self.remaining_min_hours()
        self._log('Commitment after reservation {0}'.format(commitment))
        # if we're under the needed minimum hours and we have available
        # time, then raise our commitment to the desired level
        if commitment < self.min_hours_per_week \
        and unallocated >= self.min_hours_per_week:
            commitment = self.min_hours_per_week
        self._log('Commitment after minimum weekly hours {0}'\
            .format(commitment))
        # calculate hours left on contract (subtract worked hours this week)
        week_start = utils.get_week_start(day)
        remaining = self.num_hours - self._filtered_hours_worked(week_start)
        total_allocated = self.blocks.aggregate(s=Sum('hours'))['s'] or 0
        remaining -= total_allocated
        if remaining < 0:
            remaining = 0
        self._log('Remaining {0}'.format(remaining))
        # reduce commitment to remaining hours
        if commitment > remaining:
            commitment = remaining
        self._log('Final commitment {0}'.format(commitment))
        return commitment

    def allocated_hours_for_week(self, day):
        week, next_week = utils.get_week_window(day)
        allocs = AssignmentAllocation.objects
        allocs = allocs.filter(assignment__user=self.user)
        allocs = allocs.filter(date__gte=week, date__lt=next_week)
        hours = allocs.aggregate(s=Sum('hours'))['s']
        return hours or 0

    def unallocated_hours_for_week(self, day):
        """ Calculate number of hours left to work for a week """
        allocated = self.allocated_hours_for_week(day)
        self._log('Allocated hours {0}'.format(allocated))
        try:
            schedule = PersonSchedule.objects.filter(user=self.user)[0]
        except IndexError:
            schedule = None
        if schedule:
            unallocated = schedule.hours_per_week - allocated
        else:
            unallocated = 40 - allocated
        return unallocated

    def remaining_contracts(self):
        assignments = ContractAssignment.objects.exclude(pk=self.pk)
        assignments = assignments.filter(end_date__gte=self.end_date,
                                         user=self.user)
        return assignments.order_by('-end_date')

    def remaining_min_hours(self):
        return self.remaining_contracts().aggregate(
            s=Sum('min_hours_per_week'))['s'] or 0

    class Meta:
        unique_together = (('contract', 'user'),)

    def __unicode__(self):
        return u'%s / %s' % (self.user, self.contract.project)


class AllocationManager(models.Manager):
    def during_this_week(self, user, day=None):
        week = utils.get_week_start(day=day)
        return self.get_query_set().filter(
            date=week, assignment__user=user,
            assignment__contract__status='current'
            ).exclude(hours=0)


class AssignmentAllocation(models.Model):
    assignment = models.ForeignKey(ContractAssignment, related_name='blocks')
    date = models.DateField()
    hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    @property
    def hours_worked(self):
        if not hasattr(self, '_hours_worked'):
            end_date = self.date + datetime.timedelta(weeks=1)
            self._hours_worked = self.assignment.\
                    filtered_hours_worked_with_in_window(self.date, end_date)
        return self._hours_worked or 0

    @property
    def hours_left(self):
        if not hasattr(self, '_hours_left'):
            self._hours_left = self.hours - self.hours_worked
        return self._hours_left or 0

    objects = AllocationManager()


class PersonSchedule(models.Model):
    user = models.ForeignKey(
        User,
        unique=True,
        null=True,
    )
    hours_per_week = models.DecimalField(max_digits=8, decimal_places=2,
                                         default=0)
    end_date = models.DateField()

    @property
    def furthest_end_date(self):
        assignments = self.user.assignments.order_by('-end_date')
        assignments = assignments.exclude(contract__status='complete')
        try:
            end_date = assignments.values('end_date')[0]['end_date']
        except IndexError:
            end_date = self.end_date
        return end_date

    @property
    def hours_available(self):
        today = datetime.date.today()
        weeks_remaining = (self.end_date - today).days / 7.0
        return float(self.hours_per_week) * weeks_remaining

    @property
    def hours_scheduled(self):
        if not hasattr(self, '_hours_scheduled'):
            self._hours_scheduled = 0
            now = datetime.datetime.now()
            for assignment in self.user.assignments.filter(end_date__gte=now):
                self._hours_scheduled += assignment.hours_remaining
        return self._hours_scheduled

    def __unicode__(self):
        return unicode(self.user)


class UserProfile(models.Model):
    user = models.OneToOneField(User, unique=True, related_name='profile')

    def __unicode__(self):
        return unicode(self.user)
