from dateutil.relativedelta import relativedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum, Max, Min
from django.utils import timezone

from timepiece import utils
from timepiece.crm.models import Project


class Activity(models.Model):
    """
    Represents different types of activity: debugging, developing,
    brainstorming, QA, etc...
    """
    code = models.CharField(max_length=5, unique=True, help_text='Enter a '
            'short code to describe the type of activity that took place.')
    name = models.CharField(max_length=50, help_text='Now enter a more '
            'meaningful name for the activity.')
    billable = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'timepiece_activity'  # Using legacy table name
        ordering = ('name',)
        verbose_name_plural = 'activities'


class ActivityGroup(models.Model):
    """Activities that are allowed for a project"""
    name = models.CharField(max_length=255, unique=True)
    activities = models.ManyToManyField(Activity, related_name='activity_group')

    class Meta:
        db_table = 'timepiece_activitygroup'  # Using legacy table

    def __unicode__(self):
        return self.name


class Location(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.CharField(max_length=255, unique=True)

    class Meta:
        db_table = 'timepiece_location'  # Using legacy table name

    def __unicode__(self):
        return self.name


class EntryQuerySet(models.query.QuerySet):
    """QuerySet extension to provide filtering by billable status"""

    def date_trunc(self, key='month', extra_values=None):
        select = {"day": {"date": """DATE_TRUNC('day', end_time)"""},
                  "week": {"date": """DATE_TRUNC('week', end_time)"""},
                  "month": {"date": """DATE_TRUNC('month', end_time)"""},
                  "year": {"date": """DATE_TRUNC('year', end_time)"""},
        }
        basic_values = (
            'user', 'date', 'user__first_name', 'user__last_name', 'billable',
        )
        extra_values = extra_values or ()
        qs = self.extra(select=select[key])
        qs = qs.values(*basic_values + extra_values)
        qs = qs.annotate(hours=Sum('hours')).order_by('user__last_name',
                                                      'date')
        return qs

    def timespan(self, from_date, to_date=None, span=None, current=False):
        """
        Takes a beginning date a filters entries. An optional to_date can be
        specified, or a span, which is one of ('month', 'week', 'day').
        N.B. - If given a to_date, it does not include that date, only before.
        """
        if span and not to_date:
            diff = None
            if span == 'month':
                diff = relativedelta(months=1)
            elif span == 'week':
                diff = relativedelta(days=7)
            elif span == 'day':
                diff = relativedelta(days=1)
            if diff is not None:
                to_date = from_date + diff
        datesQ = Q(end_time__gte=from_date)
        datesQ &= Q(end_time__lt=to_date) if to_date else Q()
        datesQ |= Q(end_time__isnull=True) if current else Q()
        return self.filter(datesQ)


class EntryManager(models.Manager):

    def get_query_set(self):
        qs = EntryQuerySet(self.model)
        qs = qs.select_related('activity', 'project__type')

        # ensure our select_related are added.  Without this line later calls
        # to select_related will void ours (not sure why - probably a bug
        # in Django)
        # in other words: do not remove!
        str(qs.query)

        qs = qs.extra({'billable': 'timepiece_activity.billable AND '
                                   'timepiece_attribute.billable'})
        return qs

    def date_trunc(self, key='month', extra_values=()):
        return self.get_query_set().date_trunc(key, extra_values)

    def timespan(self, from_date, to_date=None, span='month'):
        return self.get_query_set().timespan(from_date, to_date, span)


class EntryWorkedManager(models.Manager):

    def get_query_set(self):
        qs = EntryQuerySet(self.model)
        projects = utils.get_setting('TIMEPIECE_PAID_LEAVE_PROJECTS')
        return qs.exclude(project__in=projects.values())


class Entry(models.Model):
    """
    This class is where all of the time logs are taken care of
    """
    UNVERIFIED = 'unverified'
    VERIFIED = 'verified'
    APPROVED = 'approved'
    INVOICED = 'invoiced'
    NOT_INVOICED = 'not-invoiced'
    STATUSES = {
        UNVERIFIED: 'Unverified',
        VERIFIED: 'Verified',
        APPROVED: 'Approved',
        INVOICED: 'Invoiced',
        NOT_INVOICED: 'Not Invoiced',
    }

    user = models.ForeignKey(User, related_name='timepiece_entries')
    project = models.ForeignKey('crm.Project', related_name='entries')
    activity = models.ForeignKey(Activity, related_name='entries')
    location = models.ForeignKey(Location, related_name='entries')
    entry_group = models.ForeignKey('contracts.EntryGroup', blank=True,
            null=True, related_name='entries', on_delete=models.SET_NULL)
    status = models.CharField(max_length=24, choices=STATUSES.items(),
            default=UNVERIFIED)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True, db_index=True)
    seconds_paused = models.PositiveIntegerField(default=0)
    pause_time = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True)
    date_updated = models.DateTimeField(auto_now=True)

    hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    objects = EntryManager()
    worked = EntryWorkedManager()
    no_join = models.Manager()

    class Meta:
        db_table = 'timepiece_entry'  # Using legacy table name
        ordering = ('-start_time',)
        verbose_name_plural = 'entries'
        permissions = (
            ('can_clock_in', 'Can use Pendulum to clock in'),
            ('can_pause', 'Can pause and unpause log entries'),
            ('can_clock_out', 'Can use Pendulum to clock out'),
            ('view_entry_summary', 'Can view entry summary page'),
            ('view_payroll_summary', 'Can view payroll summary page'),
            ('approve_timesheet', 'Can approve a verified timesheet'),
        )

    def __unicode__(self):
        return '%s on %s' % (self.user, self.project)

    def check_overlap(self, entry_b, **kwargs):
        """Return True if the two entries overlap."""
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
                total = entry_a.get_total_seconds() + \
                        entry_b.get_total_seconds() - 1
                if total >= diff:
                    return True
            return False

    def is_overlapping(self):
        if self.start_time and self.end_time:
            entries = self.user.timepiece_entries.filter(
            Q(end_time__range=(self.start_time, self.end_time)) |
            Q(start_time__range=(self.start_time, self.end_time)) |
            Q(start_time__lte=self.start_time, end_time__gte=self.end_time))

            totals = entries.aggregate(
            max=Max('end_time'), min=Min('start_time'))

            totals['total'] = 0
            for entry in entries:
                totals['total'] = totals['total'] + entry.get_total_seconds()

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
            end = start + relativedelta(seconds=1)
        entries = self.user.timepiece_entries.filter(
            Q(end_time__range=(start, end)) |
            Q(start_time__range=(start, end)) |
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
                    raise ValidationError('Start time overlaps with '
                            '{activity} on {project} from {start_time} to '
                            '{end_time}.'.format(**entry_data))
                else:
                    entry_data['start_time'] = entry.start_time.strftime(
                        '%H:%M:%S on %m\%d\%Y')
                    entry_data['end_time'] = entry.end_time.strftime(
                        '%H:%M:%S on %m\%d\%Y')
                    raise ValidationError('Start time overlaps with '
                            '{activity} on {project} from {start_time} to '
                            '{end_time}.'.format(**entry_data))
        try:
            act_group = self.project.activity_group
            if act_group:
                activity = self.activity
                if not act_group.activities.filter(pk=activity.pk).exists():
                    name = activity.name
                    err_msg = '%s is not allowed for this project. ' % name
                    allowed = act_group.activities.filter()
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
        if end < start:
            raise ValidationError('Ending time must exceed the starting time')
        delta = (end - start)
        delta_secs = (delta.seconds + delta.days * 24 * 60 * 60)
        limit_secs = 60 * 60 * 12
        if delta_secs > limit_secs or self.seconds_paused > limit_secs:
            err_msg = 'Ending time exceeds starting time by 12 hours or more '\
                'for {0} on {1} at {2} to {3} at {4}.'.format(
                    self.project,
                    start.strftime('%m/%d/%Y'),
                    start.strftime('%H:%M:%S'),
                    end.strftime('%m/%d/%Y'),
                    end.strftime('%H:%M:%S')
                )
            raise ValidationError(err_msg)
        month_start = utils.get_month_start(start)
        next_month = month_start + relativedelta(months=1)
        entries = self.user.timepiece_entries.filter(
            Q(status=Entry.APPROVED) | Q(status=Entry.INVOICED),
            start_time__gte=month_start,
            end_time__lt=next_month
        )
        if (entries.exists() and not self.id
                or self.id and self.status == Entry.INVOICED):
            msg = 'You cannot add/edit entries after a timesheet has been ' \
                'approved or invoiced. Please correct the start and end times.'
            raise ValidationError(msg)
        return True

    def save(self, *args, **kwargs):
        self.hours = Decimal('%.2f' % round(self.total_hours, 2))
        super(Entry, self).save(*args, **kwargs)

    def get_total_seconds(self):
        """
        Determines the total number of seconds between the starting and
        ending times of this entry. If the entry is paused, the end_time is
        assumed to be the pause time. If the entry is active but not paused,
        the end_time is assumed to be now.
        """
        start = self.start_time
        end = self.end_time
        if not end:
            end = self.pause_time if self.is_paused else timezone.now()
        delta = end - start
        seconds = delta.seconds - self.get_paused_seconds()
        return seconds + (delta.days * 86400)

    def get_paused_seconds(self):
        """
        Returns the total seconds that this entry has been paused. If the
        entry is currently paused, then the additional seconds between
        pause_time and now are added to seconds_paused. If pause_time is in
        the future, no extra pause time is added.
        """
        if self.is_paused:
            date = timezone.now()
            delta = date - self.pause_time
            extra_pause = max(0, delta.seconds + (delta.days * 24 * 60 * 60))
            return self.seconds_paused + extra_pause
        return self.seconds_paused

    @property
    def total_hours(self):
        """
        Determined the total number of hours worked in this entry
        """
        total = self.get_total_seconds() / 3600.0
        #in case seconds paused are greater than the elapsed time
        if total < 0:
            total = 0
        return total

    @property
    def is_paused(self):
        """
        Determine whether or not this entry is paused
        """
        return bool(self.pause_time)

    def pause(self):
        """
        If this entry is not paused, pause it.
        """
        if not self.is_paused:
            self.pause_time = timezone.now()

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
                date = timezone.now()
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

    @property
    def is_closed(self):
        """
        Determine whether this entry has been closed or not
        """
        return bool(self.end_time)

    @property
    def is_editable(self):
        return self.status == Entry.UNVERIFIED

    @property
    def delete_key(self):
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

    @staticmethod
    def summary(user, date, end_date):
        """
        Returns a summary of hours worked in the given time frame, for this
        user.  The setting TIMEPIECE_PAID_LEAVE_PROJECTS can be used to
        separate out hours for paid leave that should not be included in the
        total worked (e.g., sick time, vacation time, etc.).  Those hours will
        be added to the summary separately using the dictionary key set in
        TIMEPIECE_PAID_LEAVE_PROJECTS.
        """
        projects = utils.get_setting('TIMEPIECE_PAID_LEAVE_PROJECTS')
        entries = user.timepiece_entries.filter(
            end_time__gt=date, end_time__lt=end_date)
        data = {
            'billable': Decimal('0'), 'non_billable': Decimal('0'),
            'invoiced': Decimal('0'), 'uninvoiced': Decimal('0'),
            'total': Decimal('0')
            }
        invoiced = entries.filter(
            status=Entry.INVOICED).aggregate(i=Sum('hours'))['i']
        uninvoiced = entries.exclude(
            status=Entry.INVOICED).aggregate(uninv=Sum('hours'))['uninv']
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


class ProjectHours(models.Model):
    week_start = models.DateField(verbose_name='start of period')
    project = models.ForeignKey('crm.Project')
    user = models.ForeignKey(User)
    hours = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        validators=[validators.MinValueValidator(Decimal("0.01"))]
    )
    published = models.BooleanField(default=False)

    def __unicode__(self):
        return "{0} on {1} for Period starting {2}".format(
                self.user.get_name_or_username(),
                self.project, self.week_start.strftime('%B %d, %Y'))

    def save(self, *args, **kwargs):
        # Ensure that week_start is the Monday of a given week.
        self.week_start = utils.get_period_start(self.week_start)
        return super(ProjectHours, self).save(*args, **kwargs)

    class Meta:
        db_table = 'timepiece_projecthours'  # Using legacy table name
        verbose_name = 'project hours entry'
        verbose_name_plural = 'project hours entries'
        unique_together = ('week_start', 'project', 'user')
