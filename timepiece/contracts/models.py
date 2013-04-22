import datetime

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models
from django.db.models import Sum
from django.template import Context
from django.template.loader import get_template

from timepiece import utils
from timepiece.entries.models import Entry, ENTRY_STATUS


class ProjectContract(models.Model):
    CONTRACT_STATUS = (
        ('upcoming', 'Upcoming'),
        ('current', 'Current'),
        ('complete', 'Complete'),
    )

    PROJECT_UNSET = 0  # Have to set existing contracts to something...
    PROJECT_FIXED = 1
    PROJECT_PRE_PAID_HOURLY = 2
    PROJECT_POST_PAID_HOURLY = 3
    PROJECT_TYPE = (   # UNSET is not an option
        (PROJECT_FIXED, 'Fixed'),
        (PROJECT_PRE_PAID_HOURLY, 'Pre-paid Hourly'),
        (PROJECT_POST_PAID_HOURLY, 'Post-paid Hourly')
    )

    name = models.CharField(max_length=255)
    projects = models.ManyToManyField('crm.Project', related_name='contracts')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(choices=CONTRACT_STATUS, default='upcoming',
                              max_length=32)
    type = models.IntegerField(choices=PROJECT_TYPE)

    class Meta:
        ordering = ('-end_date',)
        verbose_name = 'contract'
        db_table = 'timepiece_projectcontract'  # Using legacy table name.

    def __unicode__(self):
        return unicode(self.name)

    @models.permalink
    def get_admin_url(self):
        return ('admin:timepiece_projectcontract_change', [self.pk])

    @models.permalink
    def get_absolute_url(self):
        return ('view_contract', [self.pk])

    @property
    def entries(self):
        """
        All Entries worked on projects in this contract during the contract
        period.
        """
        return Entry.objects.filter(project__in=self.projects.all(),
                start_time__gte=self.start_date,
                end_time__lt=self.end_date + datetime.timedelta(days=1))

    def contracted_hours(self, approved_only=True):
        """Compute the hours contracted for this contract.
        (This replaces the old `num_hours` field.)

        :param boolean approved_only: If true, only include approved
            contract hours; if false, include pending ones too.
        :returns: The sum of the contracted hours, subject to the
            `approved_only` parameter.
        :rtype: Decimal
        """

        qset = self.contract_hours
        if approved_only:
            qset = qset.filter(status=ContractHour.APPROVED_STATUS)
        result = qset.aggregate(sum=Sum('hours'))['sum']
        return result or 0

    def pending_hours(self):
        """Compute the contract hours still in pending status"""
        qset = self.contract_hours.filter(status=ContractHour.PENDING_STATUS)
        result = qset.aggregate(sum=Sum('hours'))['sum']
        return result or 0

    @property
    def hours_assigned(self):
        """Total assigned hours for this contract."""
        if not hasattr(self, '_assigned'):
            # TODO put this in a .extra w/a subselect
            assignments = self.assignments.aggregate(s=Sum('num_hours'))
            self._assigned = assignments['s'] or 0
        return self._assigned or 0

    @property
    def hours_remaining(self):
        return self.contracted_hours() - self.hours_worked

    @property
    def hours_worked(self):
        """Number of billable hours worked on the contract."""
        if not hasattr(self, '_worked'):
            # TODO put this in a .extra w/a subselect
            entries = self.entries.filter(activity__billable=True)
            self._worked = entries.aggregate(s=Sum('hours'))['s'] or 0
        return self._worked or 0

    @property
    def nonbillable_hours_worked(self):
        """Number of non-billable hours worked on the contract."""
        if not hasattr(self, '_nb_worked'):
            # TODO put this in a .extra w/a subselect
            entries = self.entries.filter(activity__billable=False)
            self._nb_worked = entries.aggregate(s=Sum('hours'))['s'] or 0
        return self._nb_worked or 0


class ContractHour(models.Model):
    PENDING_STATUS = 1
    APPROVED_STATUS = 2
    CONTRACT_HOUR_STATUS = (
        (PENDING_STATUS, 'Pending'), # default
        (APPROVED_STATUS, 'Approved')
        )

    hours = models.DecimalField(max_digits=8, decimal_places=2,
            default=0)
    contract = models.ForeignKey(ProjectContract,
            related_name='contract_hours')
    date_requested = models.DateField()
    date_approved = models.DateField(blank=True, null=True)
    status = models.IntegerField(choices=CONTRACT_HOUR_STATUS,
            default=PENDING_STATUS)
    notes = models.TextField(blank=True)

    class Meta(object):
        verbose_name = 'contracted hours'
        verbose_name_plural = verbose_name
        db_table = 'timepiece_contracthour'  # Using legacy table name.

    def __init__(self, *args, **kwargs):
        super(ContractHour, self).__init__(*args, **kwargs)
        # Save the current values so we can report changes later
        self._original = {
            'hours': self.hours,
            'notes': self.notes,
            'status': self.status,
            'get_status_display': self.get_status_display(),
            'date_requested': self.date_requested,
            'date_approved': self.date_approved,
            'contract': self.contract if self.contract_id else None,
            }

    @models.permalink
    def get_absolute_url(self):
        return ('admin:timepiece_contracthour_change', [self.pk])

    def clean(self):
        # Note: this is called when editing in the admin, but not otherwise
        if self.status == self.PENDING_STATUS and self.date_approved:
            raise ValidationError(
                "Pending contracthours should not have an approved date, did "
                "you mean to change status to approved?"
            )

    def _send_mail(self, subject, ctx):
        # Don't go to the work unless we have a place to send it
        emails = utils.get_setting('TIMEPIECE_ACCOUNTING_EMAILS')
        if not emails:
            return
        from_email = utils.get_setting('DEFAULT_FROM_EMAIL')
        template = get_template('timepiece/contract/hours_email.txt')
        context = Context(ctx)
        msg = template.render(context)
        send_mail(
            subject=subject,
            message=msg,
            from_email=from_email,
            recipient_list=emails
        )

    def save(self, *args, **kwargs):
        # Let the date_approved default to today if it's been set approved
        # and doesn't have one
        if self.status == self.APPROVED_STATUS and not self.date_approved:
            self.date_approved = datetime.date.today()

        # If we have an email address to send to, and this record was
        # or is in pending status, we'll send an email about the change.
        if ContractHour.PENDING_STATUS in (self.status, self._original['status']):
            is_new = self.pk is None
        super(ContractHour, self).save(*args, **kwargs)
        if ContractHour.PENDING_STATUS in (self.status, self._original['status']):
            domain = Site.objects.get_current().domain
            method = 'https' if utils.get_setting('TIMEPIECE_EMAILS_USE_HTTPS')\
                else 'http'
            url = self.contract.get_absolute_url()
            ctx = {
                'new': is_new,
                'changed': not is_new,
                'deleted': False,
                'current': self,
                'previous': self._original,
                'link': '%s://%s%s' % (method, domain, url)
            }
            prefix = "New" if is_new else "Changed"
            name = self._meta.verbose_name
            subject = "%s pending %s for %s" % (prefix, name, self.contract)
            self._send_mail(subject, ctx)

    def delete(self, *args, **kwargs):
        # Note: this gets called when you delete a single item using the red
        # Delete button at the bottom while editing it in the admin - but not
        # when you delete one or more from the change list using the admin
        # action.
        super(ContractHour, self).delete(*args, **kwargs)
        # If we have an email address to send to, and this record was in
        # pending status, we'll send an email about the change.
        if ContractHour.PENDING_STATUS in (self.status, self._original['status']):
            domain = Site.objects.get_current().domain
            method = 'https' if utils.get_setting('TIMEPIECE_EMAILS_USE_HTTPS')\
                else 'http'
            url = self.contract.get_absolute_url()
            ctx = {
                'deleted': True,
                'new': False,
                'changed': False,
                'previous': self._original,
                'link': '%s://%s%s' % (method, domain, url)
            }
            contract = self._original['contract']
            name = self._meta.verbose_name
            subject = "Deleted pending %s for %s" % (name, contract)
            self._send_mail(subject, ctx)


class ContractAssignment(models.Model):
    contract = models.ForeignKey(ProjectContract, related_name='assignments')
    user = models.ForeignKey(User, related_name='assignments')
    start_date = models.DateField()
    end_date = models.DateField()
    num_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    min_hours_per_week = models.IntegerField(default=0)

    class Meta:
        unique_together = (('contract', 'user'),)
        db_table = 'timepiece_contractassignment'  # Using legacy table name.

    def __unicode__(self):
        return u'{0} / {1}'.format(self.user, self.contract)

    @property
    def entries(self):
        return Entry.objects.filter(project__in=self.contract.projects.all(),
                user=self.user, start_time__gte=self.start_date,
                end_time__lt=self.end_date + datetime.timedelta(days=1))

    @property
    def hours_remaining(self):
        return self.num_hours - self.hours_worked

    @property
    def hours_worked(self):
        if not hasattr(self, '_worked'):
            self._worked = self.entries.aggregate(s=Sum('hours'))['s'] or 0
        return self._worked or 0


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
            act_values = [(act[0], act[2]) for act in activity_totals
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
    activities = models.ManyToManyField('entries.Activity',
            related_name='activity_bundle')
    order = models.PositiveIntegerField(unique=True, blank=True, null=True)

    objects = HourGroupManager()

    def __unicode__(self):
        return self.name


class EntryGroup(models.Model):
    VALID_STATUS = ('invoiced', 'not-invoiced')
    STATUS_CHOICES = [status for status in ENTRY_STATUS
                      if status[0] in VALID_STATUS]
    user = models.ForeignKey(User, related_name='entry_group')
    project = models.ForeignKey('crm.Project', related_name='entry_group')
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


