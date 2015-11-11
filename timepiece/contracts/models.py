import datetime
from dateutil.relativedelta import relativedelta

from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import Sum
from django.template import Context
from django.template.loader import get_template
from django.conf import settings

from timepiece import utils
from timepiece.crm.models import Contact
from timepiece.entries.models import Entry, Activity
from timepiece import emails as timepiece_emails

from decimal import Decimal
from itertools import groupby
import boto

from taggit.managers import TaggableManager

class ProjectContract(models.Model):
    STATUS_UPCOMING = 'upcoming'
    STATUS_CURRENT = 'current'
    STATUS_COMPLETE = 'complete'
    CONTRACT_STATUS = {
        STATUS_UPCOMING: 'Upcoming',
        STATUS_CURRENT: 'Current',
        STATUS_COMPLETE: 'Complete',
    }

    PROJECT_UNSET = 0  # Have to set existing contracts to something...
    PROJECT_FIXED = 1
    PROJECT_PRE_PAID_HOURLY = 2
    PROJECT_POST_PAID_HOURLY = 3
    PROJECT_TYPE = {   # UNSET is not an option
        PROJECT_FIXED: 'Fixed',
        PROJECT_PRE_PAID_HOURLY: 'Pre-paid Hourly',
        PROJECT_POST_PAID_HOURLY: 'Post-paid Hourly',
    }

    PYMT_NET0  = 'net0'
    PYMT_NET15 = 'net15'
    PYMT_NET30 = 'net30'
    PYMT_NET45 = 'net45'
    PYMT_NET60 = 'net60'
    PYMT_NET75 = 'net75'
    PYMT_NET90 = 'net90'
    CONTRACT_PYMT_TERMS = {
        PYMT_NET0:  'On receipt (Net-0)',
        PYMT_NET15: 'Net-15',
        PYMT_NET30: 'Net-30',
        PYMT_NET45: 'Net-45',
        PYMT_NET60: 'Net-60',
        PYMT_NET75: 'Net-75',
        PYMT_NET90: 'Net-90',
    }

    HOURS = 1
    BUDGET = 2
    CONTRACT_LIMIT_TYPE = {
        HOURS: 'Hours',
        BUDGET: 'Budget'
    }

    CEC_CAPITAL = 'capital'
    CEC_OPERATIONAL = 'operational'
    CEC_UNKNOWN = 'unknown'
    CLIENT_EXPENSE_CATEGORIES = {
        CEC_CAPITAL: 'Capital',
        CEC_OPERATIONAL: 'Operational',
        CEC_UNKNOWN: 'Unknown'
    }


    name = models.CharField(max_length=255)
    primary_contact = models.ForeignKey(Contact)
    projects = models.ManyToManyField('crm.Project', related_name='contracts')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(choices=CONTRACT_STATUS.items(),
            default=STATUS_UPCOMING, max_length=32)
    type = models.IntegerField(choices=PROJECT_TYPE.items())
    payment_terms = models.CharField(max_length=32,
        choices=CONTRACT_PYMT_TERMS.items(), default=PYMT_NET30)
    ceiling_type = models.IntegerField(
        default=BUDGET,
        choices=CONTRACT_LIMIT_TYPE.items(),
        help_text='How is the ceiling value determined for the contract?')
    client_expense_category = models.CharField(
        choices=CLIENT_EXPENSE_CATEGORIES.items(),
        default=CEC_UNKNOWN, max_length=16)
    po_number = models.CharField(max_length=100,null=True, blank=True)
    po_line_item = models.CharField(max_length=10,null=True, blank=True)

    tags = TaggableManager()

    class Meta:
        ordering = ('name',)
        verbose_name = 'contract'
        db_table = 'timepiece_projectcontract'  # Using legacy table name.
        permissions = (
            ('view_contract', 'Can view contracts'),
        )

    def __unicode__(self):
        return unicode(self.name)

    def get_admin_url(self):
        return reverse('admin:contracts_projectcontract_change', args=[self.pk])

    def get_absolute_url(self):
        return reverse('view_contract', args=[self.pk])

    @property
    def entries(self):
        """
        All Entries worked on projects in this contract during the contract
        period.
        """
        return Entry.objects.filter(project__in=self.projects.all(),
                start_time__gte=self.start_date,
                end_time__lt=self.end_date + relativedelta(days=1))

    @property
    def increments(self):
        if self.ceiling_type == self.HOURS:
            return ContractHour.objects.filter(
                contract=self).order_by('date_requested')
        elif self.ceiling_type == self.BUDGET:
            return ContractBudget.objects.filter(
                contract=self).order_by('date_requested')
        else:
            return []

    def contract_value(self, approved_only=True):
        """Compute the hours contracted for this contract.

        :param boolean approved_only: If true, only include approved
            contract hours/budget; if false, include pending ones too.
        :returns: The sum of the contracted hours/budget, subject to the
            `approved_only` parameter.
        :rtype: Decimal
        """
        if self.ceiling_type == self.HOURS:
            return self.contracted_hours(approved_only)
        elif self.ceiling_type == self.BUDGET:
            return self.not_to_exceed(approved_only)
        else:
            return 0.0

    @property
    def display_contract_value(self):
        if self.ceiling_type == self.HOURS:
            return '{:,.2f}'.format(self.contract_value())
        elif self.ceiling_type == self.BUDGET:
            return '$ {:,.2f}'.format(self.contract_value())
        else:
            return None

    def contracted_hours(self, approved_only=True):
        """Compute the hours contracted for this contract.
        (This replaces the old `num_hours` field.)

        :param boolean approved_only: If true, only include approved
            contract hours; if false, include pending ones too.
        :returns: The sum of the contracted hours, subject to the
            `approved_only` parameter.
        :rtype: Decimal
        """

        qset = self.contracthour_set
        if approved_only:
            qset = qset.filter(status=ContractHour.APPROVED_STATUS)
        result = qset.aggregate(sum=Sum('hours'))['sum']
        return result or 0

    def not_to_exceed(self, approved_only=True):
        """Compute the not-to-exceed value for this contract.

        :param boolean approved_only: If true, only include approved
            contract budget; if false, include pending ones too.
        :returns: The sum of the contracted budget, subject to the
            `approved_only` parameter.
        :rtype: Decimal
        """

        qset = self.contractbudget_set
        if approved_only:
            qset = qset.filter(status=ContractBudget.APPROVED_STATUS)
        result = qset.aggregate(sum=Sum('budget'))['sum']
        return result or 0

    def pending_hours(self):
        """Compute the contract hours still in pending status"""
        qset = self.contracthour_set.filter(status=ContractHour.PENDING_STATUS)
        result = qset.aggregate(sum=Sum('hours'))['sum']
        return result or 0

    def pending_budget(self):
        """Compute the contract budget still in pending status"""
        qset = self.contractbudget_set.filter(status=ContractHour.PENDING_STATUS)
        result = qset.aggregate(sum=Sum('budget'))['sum']
        return result or 0

    def pending_ceiling(self):
        """Computer the contract hours or budget still in pending status"""
        if self.ceiling_type == self.HOURS:
            return self.pending_hours()
        elif self.ceiling_type == self.BUDGET:
            return self.pending_budget()
        else:
            return 0

    @property
    def hours_assigned(self):
        """Total assigned hours for this contract."""
        if not hasattr(self, '_assigned'):
            # TODO put this in a .extra w/a subselect
            assignments = self.assignments.aggregate(s=Sum('num_hours'))
            self._assigned = assignments['s'] or 0
        return self._assigned or 0

    def value_remaining(self):
        if self.ceiling_type == self.HOURS:
            return self.hours_remaining
        elif self.ceiling_type == self.BUDGET:
            return self.budget_remaining
        else:
            return None

    @property
    def value_expended(self):
        return self.contract_value() - self.value_remaining()

    def display_value_remaining(self):
        if self.ceiling_type == self.HOURS:
            return '{:,.2f}'.format(self.hours_remaining)
        elif self.ceiling_type == self.BUDGET:
            return '$ {:,.2f}'.format(self.budget_remaining)
        else:
            return None

    @property
    def hours_remaining(self):
        return self.contracted_hours() - self.hours_worked

    @property
    def budget_remaining(self):
        return self.not_to_exceed() - self.invoiced_budget

    @property
    def hours_worked(self):
        """Number of billable hours worked on the contract."""
        if not hasattr(self, '_worked'):
            # TODO put this in a .extra w/a subselect
            entries = self.entries.filter(activity__billable=True)
            self._worked = entries.aggregate(s=Sum('hours'))['s'] or 0
        return self._worked or 0

    @property
    def activity_totals(self):
        activity_totals = {}
        sorted_entries = sorted(list(self.entries.filter(
            activity__billable=True)),
            key=lambda e: e.activity.id)
        """
        an alternate approach was tried:

        for activity, group in groupby(sorted_entries,
            lambda se: se.activity.id):
            activity_totals[activity] = self.entries.filter(
                activity__id=activity).aggregate(s=Sum('hours'))['s']

        but it was found to be much slower.  Using IPython %timeit, the
        following results were found.
          - Implemented approach: 1000 loops, best of 3: 786 microsec per loop
          - Commented approach: 10 loops, best of 3: 37.1 ms per loop
        """
        for activity, group in groupby(sorted_entries, lambda se: se.activity.id):
            total = Decimal('0.0')
            for e in group:
                total += e.hours
            activity_totals[activity] = total
        return activity_totals

    @property
    def invoiced_budget(self):
        """Cost of billable hours worked on the contract."""
        if not hasattr(self, '_invoiced'):
            # TODO put this in a .extra w/a subselect
            total = Decimal('0.0')
            for activity_id, hours in self.activity_totals.items():
                total += hours * self.get_rate(activity_id)
            self._invoiced = total
        return self._invoiced or Decimal('0.0')

    @property
    def nonbillable_hours_worked(self):
        """Number of non-billable hours worked on the contract."""
        if not hasattr(self, '_nb_worked'):
            # TODO put this in a .extra w/a subselect
            entries = self.entries.filter(activity__billable=False)
            self._nb_worked = entries.aggregate(s=Sum('hours'))['s'] or 0
        return self._nb_worked or 0

    @property
    def fraction_value(self):
        """Fraction of contracted value that have been consumed.  E.g.
        if 50 hours have been worked of 100 contracted, value is 0.5.
        Or if $5,000 has been worked of $10,000 contracted, value is 0.5.
        """
        try:
            return 1.0 - (float(self.value_remaining()) / float(self.contract_value()))
        except:
            return 1.0

    @property
    def fraction_schedule(self):
        """If contract status is current, return the current date as a
        fraction of the scheduled period - e.g. if the contract period is
        June 1 to July 31, and today is July 1, then the value is
        about 0.5.

        If the contract status is not current, or either the start or end
        date is not set, returns 0.0
        """
        if self.status != ProjectContract.STATUS_CURRENT or \
            not self.start_date or \
            not self.end_date:
                return 0.0
        contract_period = (self.end_date - self.start_date).days
        if contract_period <= 0.0:
            return 0.0
        days_elapsed = (datetime.date.today() - self.start_date).days
        if days_elapsed <= 0.0:
            return 0.0
        return min(float(days_elapsed) / contract_period, 1.0)

    def get_rate(self, activity_id):
        try:
            return ContractRate.objects.get(contract=self,
                activity__id=activity_id).rate
        except:
            return self.min_rate

    @property
    def get_rates(self):
        return ContractRate.objects.filter(contract=self
            ).order_by('activity__name')

    @property
    def min_rate(self):
        if len(self.get_rates):
            return min(rate.rate for rate in self.get_rates)
        else:
            return Decimal('0.0')

    @property
    def missing_rates(self):
        activity_totals = self.activity_totals
        missing_rates = []
        for activity_id, hours in self.activity_totals.items():
            if ContractRate.objects.filter(contract=self,
                activity__id=activity_id).count()==0:
                activity = Activity.objects.get(id=activity_id)
                missing_rates.append({'activity': activity,
                                      'hours': hours,
                                      'rate': self.min_rate})
        return missing_rates

    @property
    def get_attachments(self):
        return ContractAttachment.objects.filter(contract=self).order_by('filename')

    @property
    def get_notes(self):
        return ContractNote.objects.filter(contract=self).order_by('-created_at')

    @property
    def open_general_tasks(self):
        return self.generaltask_set.filter() # status__terminal=False

class ContractNote(models.Model):
    contract = models.ForeignKey(ProjectContract)
    author = models.ForeignKey(User)
    created_at = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)
    last_edited = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey("self", null=True, blank=True)
    text = models.TextField()

    def get_thread(self, thread):
        thread.append(self)
        for n in ContractNote.objects.filter(parent=self).order_by('-created_at'):
            thread.append(n.get_thread(), thread)

    def save(self, *args, **kwargs):
        super(ContractNote, self).save(*args, **kwargs)
        url = '%s%s' % (settings.DOMAIN, reverse('view_contract', args=(self.contract.id,)))
        # send email to AAC Management
        timepiece_emails.contract_new_note(self, url)

class ContractIncrement(models.Model):
    PENDING_STATUS = 1
    APPROVED_STATUS = 2
    CONTRACT_HOUR_STATUS = (
        (PENDING_STATUS, 'Pending'), # default
        (APPROVED_STATUS, 'Approved')
        )

    contract = models.ForeignKey(ProjectContract)
    date_requested = models.DateField()
    date_approved = models.DateField(blank=True, null=True)
    status = models.IntegerField(choices=CONTRACT_HOUR_STATUS,
            default=PENDING_STATUS)
    notes = models.TextField(blank=True)

    class Meta:
        abstract = True

    def clean(self):
        # Note: this is called when editing in the admin, but not otherwise
        if self.status == self.PENDING_STATUS and self.date_approved:
            raise ValidationError(
                "Pending contract increment should not have an approved date, did "
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
        if ContractIncrement.PENDING_STATUS in (self.status, self._original['status']):
            is_new = self.pk is None
        super(ContractIncrement, self).save(*args, **kwargs)
        if ContractIncrement.PENDING_STATUS in (self.status, self._original['status']):
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
        super(ContractIncrement, self).delete(*args, **kwargs)
        # If we have an email address to send to, and this record was in
        # pending status, we'll send an email about the change.
        if ContractIncrement.PENDING_STATUS in (self.status, self._original['status']):
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

class ContractHour(ContractIncrement):
    hours = models.DecimalField(max_digits=8, decimal_places=2,
            default=0)

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

    def get_absolute_url(self):
        return reverse('admin:contracts_contracthour_change', args=[self.pk])

    @property
    def value(self):
        return self.hours

    @property
    def edit_url(self):
        return reverse('edit_contract_hours',
            args=(self.contract.id, self.id))

    @property
    def delete_url(self):
        return reverse('delete_contract_hours',
            args=(self.contract.id, self.id))

class ContractBudget(ContractIncrement):
    budget = models.DecimalField(max_digits=11, decimal_places=2,
            default=0)

    class Meta(object):
        verbose_name = 'contracted budget'
        verbose_name_plural = verbose_name

    def __init__(self, *args, **kwargs):
        super(ContractBudget, self).__init__(*args, **kwargs)
        # Save the current values so we can report changes later
        self._original = {
            'budget': self.budget,
            'notes': self.notes,
            'status': self.status,
            'get_status_display': self.get_status_display(),
            'date_requested': self.date_requested,
            'date_approved': self.date_approved,
            'contract': self.contract if self.contract_id else None,
            }
    def __unicode__(self):
        return '%s - %f' % (self.contract, self.budget)

    def get_absolute_url(self):
        return reverse('admin:contracts_contracthour_change', args=[self.pk])

    @property
    def value(self):
        return self.budget

    @property
    def edit_url(self):
        return reverse('edit_contract_budget',
            args=(self.contract.id, self.id))

    @property
    def delete_url(self):
        return reverse('delete_contract_budget',
            args=(self.contract.id, self.id))


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
                end_time__lt=self.end_date + relativedelta(days=1))

    @property
    def hours_remaining(self):
        return self.num_hours - self.hours_worked

    @property
    def hours_worked(self):
        if not hasattr(self, '_worked'):
            self._worked = self.entries.aggregate(s=Sum('hours'))['s'] or 0
        return self._worked or 0


class ContractRate(models.Model):
    contract = models.ForeignKey(ProjectContract)
    activity = models.ForeignKey(Activity)
    rate = models.DecimalField(max_digits=6, decimal_places=2,
            default=0, verbose_name='Rate per Hour')

    class Meta:
        unique_together = (("contract", "activity"),)

    def __unicode__(self):
        return '%s - %s: %.2f' % (self.contract, self.activity.name, self.rate)

    @property
    def get_hours(self):
        return self.contract.entries.filter(activity=self.activity).aggregate(
            s=Sum('hours'))['s']

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

    class Meta:
        db_table = 'timepiece_hourgroup'  # Using legacy table name.

    def __unicode__(self):
        return self.name


class EntryGroup(models.Model):
    INVOICED = Entry.INVOICED
    NOT_INVOICED = Entry.NOT_INVOICED
    STATUSES = {
        INVOICED: 'Invoiced',
        NOT_INVOICED: 'Not Invoiced',
    }

    user = models.ForeignKey(User, related_name='entry_group')
    project = models.ForeignKey('crm.Project', related_name='entry_group', blank=True, null=True)
    single_project = models.BooleanField(default=True)
    contract = models.ForeignKey(ProjectContract, blank=True, null=True)
    status = models.CharField(max_length=24, choices=STATUSES.items(),
                              default=INVOICED)
    number = models.CharField("Reference #", max_length=50, blank=True,
                              null=True)
    comments = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    start = models.DateField(blank=True, null=True)
    end = models.DateField()

    class Meta:
        db_table = 'timepiece_entrygroup'  # Using legacy table name.

    def delete(self):
        self.entries.update(status=Entry.APPROVED)
        super(EntryGroup, self).delete()

    def __unicode__(self):
        if self.single_project:
            invoice_data = {
                'number': self.number,
                'status': self.status,
                'project': self.project,
                'end': self.end.strftime('%b %Y'),
            }
        else:
            invoice_data = {
                'number': self.number,
                'status': self.status,
                'project': self.contract,
                'end': self.end.strftime('%b %Y'),
            }
        return u'Entry Group ' + \
               u'%(number)s: %(status)s - %(project)s - %(end)s' % invoice_data


class ContractAttachment(models.Model):
    contract = models.ForeignKey(ProjectContract)
    bucket = models.CharField(max_length=64)
    uuid = models.TextField() # AWS S3 uuid
    filename = models.CharField(max_length=128)
    upload_datetime = models.DateTimeField(auto_now_add=True)
    uploader = models.ForeignKey(User)
    description = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return "%s: %s" % (self.contract, self.filename)

    def get_download_url(self):
        conn = boto.connect_s3(settings.AWS_UPLOAD_CLIENT_KEY,
            settings.AWS_UPLOAD_CLIENT_SECRET_KEY)
        bucket = conn.get_bucket(self.bucket)
        s3_file_path = bucket.get_key(self.uuid)
        url = s3_file_path.generate_url(expires_in=15) # expiry time is in seconds
        return url
