import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum, Max, Min

try:
    from django.utils import timezone
except ImportError:
    from timepiece import timezone

from timepiece import utils


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
    tracker_url = models.CharField(max_length=255, blank=True, null=False,
        default="")
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

    class Meta:
        ordering = ('name', 'status', 'type',)
        permissions = (
            ('view_project', 'Can view project'),
            ('email_project_report', 'Can email project report'),
            ('view_project_time_sheet', 'Can view project time sheet'),
            ('export_project_time_sheet', 'Can export project time sheet'),
            ('generate_project_invoice', 'Can generate project invoice'),
        )

    def __unicode__(self):
        return self.name

    def trac_url(self):
        return settings.TRAC_URL % self.tracker_url


class RelationshipType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.CharField(max_length=255, unique=True, editable=False)

    def save(self, *args, **kwargs):
        queryset = RelationshipType.objects.all()
        if self.id:
            queryset = queryset.exclude(id__exact=self.id)
        self.slug = utils.slugify_uniquely(self.name, queryset, 'slug')
        super(RelationshipType, self).save(*args, **kwargs)

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


class HourGroupManager(models.Manager):
    def summaries(self, entries):
        #Get the list of bundle names and hour sums
        bundled_entries = entries.values('activity__activity_bundle',
                                         'activity__activity_bundle__name')
        bundled_entries = bundled_entries.annotate(Sum('hours'))
        bundled_entries = bundled_entries.order_by(
                                            'activity__activity_bundle__order',
                                            'activity__activity_bundle__name'
        )
        bundled_totals = list(bundled_entries.values_list(
                                             'activity__activity_bundle__name',
                                             'activity__activity_bundle',
                                             'hours__sum')
        )
        #Get the list of activity names and hour sums
        activity_entries = entries.values('activity', 'activity__name',
                                          'activity__activity_bundle')
        activity_entries = activity_entries.annotate(Sum('hours'))
        activity_entries = activity_entries.order_by('activity')
        activity_totals = list(activity_entries.values_list(
                                                   'activity__name',
                                                   'activity__activity_bundle',
                                                   'hours__sum')
        )
        totals = {}
        other_values = ()
        for bundle in bundled_totals:
            bundle_key, bundle_value = bundle[0], bundle[2]
            act_values = [(act[0], act[2]) for act in activity_totals \
                          if act[1] == bundle[1]]
            if bundle_key is not None:
                totals[bundle_key] = (bundle_value, act_values)
            else:
                other_values = (bundle_value, act_values)
        totals = sorted(totals.items())
        if other_values:
            totals.append(('Other', other_values))
        all_totals = sum([bt[2] for bt in bundled_totals])
        totals.append(('Total', (all_totals, [])))
        return totals


class HourGroup(models.Model):
    """Activities that are bundled together for billing"""

    name = models.CharField(max_length=255, unique=True)
    activities = models.ManyToManyField(
        Activity,
        related_name='activity_bundle',
    )
    order = models.PositiveIntegerField(unique=True, blank=True, null=True)

    objects = HourGroupManager()

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


class EntryQuerySet(models.query.QuerySet):
    """QuerySet extension to provide filtering by billable status"""

    def date_trunc(self, key='month', extra_values=None):
        select = {"day": {"date": """DATE_TRUNC('day', end_time)"""},
                  "week": {"date": """DATE_TRUNC('week', end_time)"""},
                  "month": {"date": """DATE_TRUNC('month', end_time)"""},
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

    def timespan(self, from_date, to_date=None, span=None):
        """
        Takes a beginning date a filters entries. An optional to_date can be
        specified, or a span, which is one of ('month', 'week', 'day').
        N.B. - If given a to_date, it does not include that date, only before.
        """
        if span and not to_date:
            diff = None
            if span == 'month':
                diff = relativedelta(months=1)
            if span == 'week':
                diff = relativedelta(days=7)
            if span == 'day':
                diff = relativedelta(days=1)
            if diff is not None:
                to_date = from_date + diff

        datesQ = Q()
        datesQ &= Q(end_time__gte=from_date)
        datesQ &= Q(end_time__lt=to_date) if to_date else Q()
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
    end_time = models.DateTimeField(blank=True, null=True, db_index=True)
    seconds_paused = models.PositiveIntegerField(default=0)
    pause_time = models.DateTimeField(blank=True, null=True)
    comments = models.TextField(blank=True)
    date_updated = models.DateTimeField(auto_now=True)

    hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    objects = EntryManager()
    worked = EntryWorkedManager()
    no_join = models.Manager()

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
        if end <= start:
            raise ValidationError('Ending time must exceed the starting time')
        delta = (end - start)
        delta_secs = (delta.seconds + delta.days * 24 * 60 * 60)
        limit_secs = 60 * 60 * 12
        if delta_secs > limit_secs or self.seconds_paused > limit_secs:
            err_msg = 'Ending time exceeds starting time by 12 hours or more '\
                'for {0} on {1} at {2} to {3} at {4}.'.format(
                    self.project.name,
                    start.strftime('%m/%d/%Y'),
                    start.strftime('%H:%M:%S'),
                    end.strftime('%m/%d/%Y'),
                    end.strftime('%H:%M:%S')
                )
            raise ValidationError(err_msg)
        month_start = utils.get_month_start(start)
        next_month = month_start + relativedelta(months=1)
        entries = self.user.timepiece_entries.filter(
            Q(status='approved') | Q(status='invoiced'),
            start_time__gte=month_start,
            end_time__lt=next_month
        )
        if (entries.exists() and not self.id
                or self.id and self.status == 'invoiced'):
            msg = 'You cannot add/edit entries after a timesheet has been ' \
                'approved or invoiced. Please correct the start and end times.'
            raise ValidationError(msg)
        return True

    def save(self, *args, **kwargs):
        self.hours = Decimal('%.2f' % round(self.total_hours, 2))
        super(Entry, self).save(*args, **kwargs)

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
                self.start_time = timezone.now()

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

    @staticmethod
    def summary(user, date, end_date):
        """
        Returns a summary of hours worked in the given time frame, for this
        user.  The setting TIMEPIECE_PROJECTS can be used to separate out hours
        for paid leave that should not be included in the total worked (e.g.,
        sick time, vacation time, etc.).  Those hours will be added to the
        summary separately using the dictionary key set in TIMEPIECE_PROJECTS.
        """
        projects = getattr(settings, 'TIMEPIECE_PROJECTS', {})
        entries = user.timepiece_entries.filter(
            end_time__gt=date, end_time__lt=end_date)
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
            ('view_payroll_summary', 'Can view payroll summary page'),
            ('approve_timesheet', 'Can approve a verified timesheet'),
        )


class EntryGroup(models.Model):
    VALID_STATUS = ('invoiced', 'not-invoiced')
    STATUS_CHOICES = [status for status in ENTRY_STATUS \
                      if status[0] in VALID_STATUS]
    user = models.ForeignKey(User, related_name='entry_group')
    project = models.ForeignKey(Project, related_name='entry_group')
    status = models.CharField(max_length=24, choices=STATUS_CHOICES,
                              default='invoiced')
    number = models.CharField("Reference #", max_length=50, blank=True,
                              null=True)
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
        return u'Entry Group ' + \
               u'%(number)s: %(status)s - %(project)s - %(end)s' % invoice_data


# Add a utility method to the User class that will tell whether or not a
# particular user has any unclosed entries
User.clocked_in = property(lambda user: user.timepiece_entries.filter(
    end_time__isnull=True).count() > 0)


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
            weeks = utils.get_week_window(timezone.now())
            try:
                end_date = self.end_date.date()
                start_date = self.start_date.date()
            except:
                end_date = self.end_date
                start_date = self.start_date
            if end_date < weeks[1].date() \
            and end_date >= weeks[0].date():
                self._priority_type = 0
            elif start_date < weeks[1].date() \
            and start_date >= weeks[0].date():
                self._priority_type = 1
            else:
                self._priority_type = 2
        return self._priority_type

    @property
    def this_weeks_priority_type(self):
        type_list = ['ending', 'starting', 'ongoing', ]
        return type_list[self.this_weeks_priority_number]

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


class UserProfile(models.Model):
    user = models.OneToOneField(User, unique=True, related_name='profile')
    hours_per_week = models.DecimalField(max_digits=8, decimal_places=2,
                                         default=40)

    def __unicode__(self):
        return unicode(self.user)


class ProjectHours(models.Model):
    week_start = models.DateField(verbose_name='start of week')
    project = models.ForeignKey(Project)
    user = models.ForeignKey(User)
    hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    published = models.BooleanField(default=False)

    def __unicode__(self):
        return "{0} on {1} for Week of {2}".format(self.user.get_full_name(),
                self.project, self.week_start.strftime('%B %d, %Y'))

    def save(self, *args, **kwargs):
        # Ensure that week_start is the Monday of a given week.
        self.week_start = utils.get_week_start(self.week_start)
        return super(ProjectHours, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'project hours entry'
        verbose_name_plural = 'project hours entries'
        unique_together = ('week_start', 'project', 'user')
