from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import get_model, Sum, Q
import datetime
import sys, traceback
from decimal import Decimal
from itertools import groupby
from timepiece.utils import get_active_entry, get_setting
from timepiece.models import MongoAttachment

from holidays.models import Holiday

from taggit.managers import TaggableManager

import boto
import workdays

try:
    from wiki.models.urlpath import URLPath
except:
    pass

try:
    from project_toolbox_main import settings
    from timepiece import emails as timepiece_emails
except:
    pass

try:
    import googlemaps # for geocoding locations
    import ystockquote # for getting stock prices
except:
    pass

# Add a utility method to the User class that will tell whether or not a
# particular user has any unclosed entries
_clocked_in = lambda user: bool(get_active_entry(user))
User.add_to_class('clocked_in', property(_clocked_in))


# Utility method to get user's name, falling back to username.
_get_name_or_username = lambda user: user.get_full_name() or user.username
User.add_to_class('get_name_or_username', _get_name_or_username)


_get_absolute_url = lambda user: reverse('view_user', args=(user.pk,))
User.add_to_class('get_absolute_url', _get_absolute_url)


class Department(models.Model):
    DEPARTMENTS = (
        ('admin','Admin'),
        ('construction','Construction'),
        ('elec-avionics', 'Electrical/Avionics'),
        ('finance','Finance'),
        ('hr','Human Resources'),
        ('integration', 'Integration'),
        ('it','Information Technology'),
        ('marketing','Marketing'),
        ('mech', 'Mechanical Systems'),
        ('ops','Operations'),
        ('sales','Sales'),
        ('struct', 'Structures'),
        ('tech-serv', 'Technical Services'),
        ('other', 'Other'),
    )
    name=models.CharField(max_length=16,
      choices=DEPARTMENTS,
      default='other')
      ## TODO Actually make the department class with options and not a static, hardcoded list.

class UserProfile(models.Model):
    SALARY = 'salary'
    HOURLY = 'hourly'
    INACTIVE = 'inactive'
    EXTERNAL = 'external'
    EMPLOYEE_TYPES = {
        SALARY: 'Salary',
        HOURLY: 'Hourly',
        INACTIVE: 'Inactive',
        EXTERNAL: 'External',
    }

    user = models.OneToOneField(User, unique=True, related_name='profile')
    business = models.ForeignKey('Business')
    employee_type = models.CharField(max_length=24, choices=EMPLOYEE_TYPES.items(), default=INACTIVE)
    earns_pto = models.BooleanField(default=False, help_text='Does the employee earn Paid Time Off?')
    earns_holiday_pay = models.BooleanField(default=False, help_text='Does the employee earn Holiday Pay?')
    pto_accrual = models.FloatField(default=0.0, verbose_name='PTO Accrual Amount', help_text='Number of PTO hours earned per pay period for the employee.')
    hire_date = models.DateField(blank=True, null=True)
    department = models.CharField(max_length=16,
      choices=Department.DEPARTMENTS,
      default='other')

    weekly_schedule = models.CharField(max_length=128, default='0,0,0,0,0,0,0')
    utilization = models.FloatField(default=80,
        help_text='The percentage of time the employee should spend on billable work as opposed to non-billable work.',
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])

    class Meta:
        db_table = 'timepiece_userprofile'  # Using legacy table name.

    def __unicode__(self):
        return unicode(self.user)

    @property
    def week_schedule(self):
        return [float(val) for val in self.weekly_schedule.split(',')]

    def week_dict(self):
        return {0: self.get_monday_schedule,
                1: self.get_tuesday_schedule,
                2: self.get_wednesday_schedule,
                3: self.get_thursday_schedule,
                4: self.get_friday_schedule,
                5: self.get_saturday_schedule,
                6: self.get_sunday_schedule}

    @property
    def get_utilization(self):
        return self.utilization / 100.0

    @property
    def exceeds_utilization(self):
        start_week = datetime.date.today()
        activity_goals = ActivityGoal.objects.filter(
            employee=self.user, end_date__gte=start_week,
            project__status=get_setting('TIMEPIECE_DEFAULT_PROJECT_STATUS'))

        # determine holidays and add time (whether employee is paid or not)
        holidays = [h['date'] for h in Holiday.holidays_between_dates(
            start_week, start_week + datetime.timedelta(days=700),
            {'paid_holiday': True})]

        billable_coverage = {}

        for activity_goal in activity_goals:
            start_date = start_week if activity_goal.date < start_week \
                else activity_goal.date

            end_date = activity_goal.end_date
            num_workdays = max(workdays.networkdays(start_date, end_date,
                holidays), 1)
            ag_hours_per_workday = activity_goal.get_remaining_hours / Decimal(num_workdays)

            for i in range((end_date-start_date).days + 1):
                date = start_date + datetime.timedelta(days=i)
                if workdays.networkdays(date, date, holidays):
                    if str(date) not in billable_coverage:
                        billable_coverage[str(date)] = 0.0
                    if activity_goal.project.type.billable and activity_goal.activity.billable:
                        billable_coverage[str(date)] += float(ag_hours_per_workday)
                        if billable_coverage[str(date)] > self.utilization_per_week:
                            return True

        # if we have not exited with a True already, then it is False
        return False

    @property
    def hours_per_week(self):
        return sum(self.week_schedule)

    @property
    def utilization_per_week(self):
        return (float(self.hours_per_week)/5.0) * self.get_utilization

    @property
    def get_sunday_schedule(self):
        return self.week_schedule[0]

    @property
    def get_monday_schedule(self):
        return self.week_schedule[1]

    @property
    def get_tuesday_schedule(self):
        return self.week_schedule[2]

    @property
    def get_wednesday_schedule(self):
        return self.week_schedule[3]

    @property
    def get_thursday_schedule(self):
        return self.week_schedule[4]

    @property
    def get_friday_schedule(self):
        return self.week_schedule[5]

    @property
    def get_saturday_schedule(self):
        return self.week_schedule[6]

    @property
    def get_pto(self):
        pto = PaidTimeOffLog.objects.filter(
            user_profile=self, pto=True).aggregate(Sum('amount'))['amount__sum']
        if pto:
            return pto
        else:
            return Decimal('0.0')

    # suggest that a cron job be setup to call this function on a monthly basis
    @classmethod
    def accrue_pto(cls, date=datetime.date.today()):
        for employee in UserProfile.objects.filter(user__is_active=True, earns_pto=True, pto_accrual__gt=0.0):
            pto_log = PaidTimeOffLog(user_profile=employee,
                date=date,
                amount=employee.pto_accrual,
                comment='Automated pay period accrual.')
            pto_log.save()


class LimitedAccessUserProfile(models.Model):
    profile = models.OneToOneField(UserProfile, unique=True, related_name='limited')
    seating = models.CharField(max_length=8, blank=True,
        verbose_name='Airplane Seating Preference',
        choices=(('window', 'Window'), ('aisle', 'Aisle')))
    ground_transportation = models.TextField(
        verbose_name='Rental Car / Shuttle / Taxi', blank=True)
    hotel_brand = models.CharField(max_length=16, blank=True,
        choices=(('Hilton', 'Hilton'),
                 ('Marriott', 'Marriott'),
                 ('IGH', 'IGH')))
    hotel_accommodatations = models.TextField(
        verbose_name='Hotel Accommodations', blank=True)
    frequent_flyer = models.TextField(blank=True,
        verbose_name='Frequeny Flyer #s')
    rental_car = models.TextField(blank=True,
        verbose_name='Rental Car Loyalty #s')
    hotel = models.TextField(blank=True,
        verbose_name='Hotel Loyalty #s')
    gift_card = models.TextField(blank=True,
        verbose_name='Preferred Gift Card')
    coffee_shops = models.TextField(blank=True,
        verbose_name='Preferred Coffee Shops')
    other_gift = models.TextField(blank=True,
        verbose_name='Other Gift Preferences')
    coffees = models.TextField(blank=True,
        verbose_name='In Office Coffees')
    teas = models.TextField(blank=True,
        verbose_name='In Office Teas')
    snacks = models.TextField(blank=True,
        verbose_name='In Office Snacks')
    sandwich = models.TextField(blank=True,
        verbose_name='Sandwich & Condiments')
    soup = models.TextField(blank=True)
    salad = models.TextField(blank=True,
        verbose_name='Salad Type and Dressing')
    pizza = models.TextField(blank=True)
    pasts = models.TextField(blank=True, verbose_name='Pasta')
    chipotle = models.TextField(blank=True)
    other = models.TextField(blank=True)
    birthday_celebration = models.BooleanField(default=True)
    birthday_month = models.IntegerField(null=True, blank=True,
        choices=((1,  'January'),
                 (2,  'February'),
                 (3,  'March'),
                 (4,  'April'),
                 (5,  'May'),
                 (6,  'June'),
                 (7,  'July'),
                 (8,  'August'),
                 (9,  'September'),
                 (10, 'October'),
                 (11, 'November'),
                 (12, 'December'))
    )
    hobbies = models.TextField(blank=True)

    class Meta:
        permissions = (('can_view_limited_profile', 'Can view limited user profile'))


class PaidTimeOffRequest(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    DENIED = 'denied'
    PROCESSED = 'processed'
    MODIFIED = 'modified'
    STATUSES = {
        PENDING: 'Pending',
        APPROVED: 'Approved',
        DENIED: 'Denied',
        PROCESSED: 'Processed',
        MODIFIED: 'Modified',
    }
    user_profile = models.ForeignKey(UserProfile, verbose_name='Employee')
    request_date = models.DateTimeField(auto_now_add=True)
    pto = models.BooleanField(verbose_name='Select for Paid Time Off (Unselect for Unpaid Time Off)', default=True, help_text='Is the request for Paid Time Off (checked) or Unpaid Time Off (unchecked)?')
    pto_start_date = models.DateField(verbose_name='Time Off Start Date', blank=True, null=True)
    pto_end_date = models.DateField(verbose_name='Time Off End Date', blank=True, null=True)
    amount = models.DecimalField(verbose_name='Number of Hours', max_digits=7, decimal_places=2)
    comment = models.TextField(verbose_name='Reason / Description', blank=True)
    approval_date = models.DateTimeField(blank=True, null=True)
    approver = models.ForeignKey(User, related_name='pto_approver', blank=True, null=True,
      on_delete=models.SET_NULL)
    process_date = models.DateTimeField(blank=True, null=True)
    processor = models.ForeignKey(User, related_name='pto_processor', blank=True, null=True,
      on_delete=models.SET_NULL)
    status = models.CharField(max_length=24, choices=STATUSES.items(), default=PENDING)
    approver_comment = models.TextField(verbose_name='Reason / Note', blank=True)

    class Meta:
        ordering = ('user_profile', '-pto_start_date',)
        permissions = (("can_approve_pto_requests", "Can approve PTO requests"),
                       ("can_process_pto_requests", "Can payroll process PTO requests"), )

    def __unicode__(self):
        return '%s %s to %s %s (%s)' % (self.user_profile, str(self.pto_start_date), str(self.pto_end_date), str(self.amount), str(self.approver) if self.approver else 'not approved')

    def get_absolute_url(self):
        return '/timepiece/pto'#reverse('view_project', args=(self.pk,))


class PaidTimeOffLog(models.Model):
    user_profile = models.ForeignKey(UserProfile)
    date = models.DateField()
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    comment = models.TextField(blank=True)
    pto_request = models.ForeignKey(PaidTimeOffRequest, blank=True, null=True,
      on_delete=models.CASCADE)
    pto = models.BooleanField(default=True, help_text='Select for Paid Time Off (Unselect for Unpaid Time Off)')

    class Meta:
        ordering = ('user_profile', '-date',)

    def __unicode__(self):
        return '%s %s %f' % (self.user_profile, str(self.date), float(self.amount))

    def get_time_entry(self):
        try:
            return self.entry_set.get()
        except:
            return None


class TypeAttributeManager(models.Manager):
    """Object manager for type attributes."""

    def get_query_set(self):
        qs = super(TypeAttributeManager, self).get_query_set()
        return qs.filter(type=Attribute.PROJECT_TYPE)


class StatusAttributeManager(models.Manager):
    """Object manager for status attributes."""

    def get_query_set(self):
        qs = super(StatusAttributeManager, self).get_query_set()
        return qs.filter(type=Attribute.PROJECT_STATUS)


class Attribute(models.Model):
    PROJECT_TYPE = 'project-type'
    PROJECT_STATUS = 'project-status'
    ATTRIBUTE_TYPES = {
        PROJECT_TYPE: 'Project Type',
        PROJECT_STATUS: 'Project Status',
    }
    SORT_ORDER_CHOICES = [(x, x) for x in xrange(-20, 21)]

    type = models.CharField(max_length=32, choices=ATTRIBUTE_TYPES.items())
    label = models.CharField(max_length=255)
    sort_order = models.SmallIntegerField(null=True, blank=True,
            choices=SORT_ORDER_CHOICES)
    enable_timetracking = models.BooleanField(default=False,
            help_text='Enable time tracking functionality for projects '
            'with this type or status.')
    billable = models.BooleanField(default=False)

    objects = models.Manager()
    types = TypeAttributeManager()
    statuses = StatusAttributeManager()

    class Meta:
        db_table = 'timepiece_attribute'  # Using legacy table name.
        unique_together = ('type', 'label')
        ordering = ('sort_order',)

    def __unicode__(self):
        return self.label


class Business(models.Model):
    BIZ_CLASS = (('client', 'Client'),
                 ('vendor', 'Vendor'),
                 ('org', 'Organization'),
                 ('other', 'Other'))

    BIZ_STATUS = (('evaluation', 'Evaluation'),
                  ('prospective', 'Prospective'),
                  ('approved', 'Approved'),
                  ('not-approved', 'Not Approved'),
                  ('other', 'Other'))

    BIZ_INDUSTRIES = (('aerospace', 'Aerospace'),
                      ('airlines', 'Airlines'),
                      ('avionics', 'Avionics'),
                      ('engineering', 'Engineering'),
                      ('shippping', 'Shipping'),
                      ('transportation', 'Transportation'),
                      ('other', 'Other'))

    STATES = (('AL', 'Alabama'),
              ('AK', 'Alaska'),
              ('AZ', 'Arizona'),
              ('AR', 'Arkansas'),
              ('CA', 'California'),
              ('CO', 'Colorado'),
              ('CT', 'Connecticut'),
              ('DE', 'Delaware'),
              ('FL', 'Florida'),
              ('GA', 'Georgia'),
              ('HI', 'Hawaii'),
              ('ID', 'Idaho'),
              ('IL', 'Illinois'),
              ('IN', 'Indiana'),
              ('IA', 'Iowa'),
              ('KS', 'Kansas'),
              ('KY', 'Kentucky'),
              ('LA', 'Louisiana'),
              ('ME', 'Maine'),
              ('MD', 'Maryland'),
              ('MA', 'Massachusetts'),
              ('MI', 'Michigan'),
              ('MN', 'Minnesota'),
              ('MS', 'Mississippi'),
              ('MO', 'Missouri'),
              ('MT', 'Montana'),
              ('NE', 'Nebraska'),
              ('NV', 'Nevada'),
              ('NH', 'New Hampshire'),
              ('NJ', 'New Jersey'),
              ('NM', 'New Mexico'),
              ('NY', 'New York'),
              ('NC', 'North Carolina'),
              ('ND', 'North Dakota'),
              ('OH', 'Ohio'),
              ('OK', 'Oklahoma'),
              ('OR', 'Oregon'),
              ('PA', 'Pennsylvania'),
              ('RI', 'Rhode Island'),
              ('SC', 'South Carolina'),
              ('SD', 'South Dakota'),
              ('TN', 'Tennessee'),
              ('TX', 'Texas'),
              ('UT', 'Utah'),
              ('VT', 'Vermont'),
              ('VA', 'Virginia'),
              ('WA', 'Washington'),
              ('WV', 'West Virginia'),
              ('WI', 'Wisconsin'),
              ('WY', 'Wyoming'))

    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=3, blank=True, unique=True)
    #email = models.EmailField(blank=True)
    poc = models.ForeignKey(User, related_name='business_poc_old', verbose_name='Old Primary Contact (User)', blank=True, null=True)
    primary_contact = models.ForeignKey('Contact', related_name='business_poc', verbose_name='Primary Contact', blank=True, null=True)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    external_id = models.CharField(max_length=32, blank=True)

    classification = models.CharField(max_length=8, blank=True, choices=BIZ_CLASS)
    active = models.BooleanField(default=False)
    status = models.CharField(max_length=16, null=True, blank=True, choices=BIZ_STATUS)
    account_owner = models.ForeignKey(User, blank=True, null=True, related_name='biz_account_holder')

    billing_street = models.CharField(max_length=255, blank=True)
    billing_street_2=models.CharField(max_length=255, blank = True)
    billing_city = models.CharField(max_length=255, blank=True)
    billing_state = models.CharField(max_length=2, blank=True, choices=STATES)
    billing_postalcode = models.CharField(max_length=32, blank=True)
    billing_mailstop = models.CharField(max_length=16, blank=True, verbose_name='Billing Zip+4')
    billing_country = models.CharField(max_length=128, blank=True)
    billing_lat = models.FloatField(blank=True, null=True, verbose_name='Billing Latitude', help_text='This is automatically set using the Google Maps Geocode API on save.')
    billing_lon = models.FloatField(blank=True, null=True, verbose_name='Billing Longitude', help_text='This is automatically set using the Google Maps Geocode API on save.')

    shipping_street = models.CharField(max_length=255, blank=True)
    shipping_street_2= models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=255, blank=True)
    shipping_state = models.CharField(max_length=2, blank=True, choices=STATES)
    shipping_postalcode = models.CharField(max_length=32, blank=True)
    shipping_mailstop = models.CharField(max_length=16, blank=True, verbose_name='Shipping Zip+4')
    shipping_country = models.CharField(max_length=128, blank=True)
    shipping_lat = models.FloatField(blank=True, null=True, verbose_name='Shipping Latitude', help_text='This is automatically set using the Google Maps Geocode API on save.')
    shipping_lon = models.FloatField(blank=True, null=True, verbose_name='Shipping Longitude', help_text='This is automatically set using the Google Maps Geocode API on save.')

    phone = models.CharField(max_length=16, blank=True)
    fax = models.CharField(max_length=16, blank=True)
    website = models.CharField(max_length=255, blank=True)

    account_number = models.CharField(max_length=255, blank=True)
    industry = models.CharField(max_length=64, blank=True, choices=BIZ_INDUSTRIES)
    ownership = models.CharField(max_length=255, blank=True)
    annual_revenue = models.FloatField(null=True, blank=True)
    num_of_employees = models.PositiveIntegerField(null=True, blank=True, verbose_name='Number of Employees')
    ticker_symbol = models.CharField(max_length=32, blank=True)

    tags = TaggableManager()

    class Meta:
        db_table = 'timepiece_business'  # Using legacy table name.
        ordering = ('name',)
        verbose_name_plural = 'Businesses'
        permissions = (
            ('view_business', 'Can view businesses'),
        )

    def __unicode__(self):
        return self.get_display_name()

    def get_absolute_url(self):
        return reverse('view_business', args=(self.pk,))

    def get_display_name(self):
        if self.short_name:
            return '%s: %s' % (self.short_name, self.name)
        else:
            return self.name

    @property
    def current_stock_value(self):
        if self.ticker_symbol:
            try:
                return float(ystockquote.get_price(self.ticker_symbol))
            except:
                return 0.0
        else:
            return 0.0

    @property
    def get_notes(self):
        return BusinessNote.objects.filter(business=self).order_by('-created_at')

    @property
    def get_attachments(self):
        return BusinessAttachment.objects.filter(
            business=self).order_by('upload_time')

    @property
    def get_departments(self):
        return BusinessDepartment.objects.filter(business=self).order_by('short_name')

    def clean(self):
        # check for uniqueness of part_number_id
        pass

    def save(self):
        try:
            gmaps = googlemaps.Client(
                key=settings.GOOGLE_SERVER_API_KEY,
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET)

            try:
                # geocode billing address
                if (self.billing_street and self.billing_city and
                    self.billing_state and self.billing_postalcode and
                    self.billing_country):
                    gc = gmaps.geocode('%s, %s, %s %s-%s, %s' % (
                        self.billing_street, self.billing_city,
                        self.billing_state, self.billing_postalcode,
                        self.billing_postalcode, self.billing_country))
                    if len(gc) == 1:
                        self.billing_lat = float(
                            gc[0]['geometry']['location']['lat'])
                        self.billing_lon = float(
                            gc[0]['geometry']['location']['lng'])
            except:
                self.billing_lat = None
                self.billing_lon = None

            try:
                # geocode shipping address
                if (self.shipping_street and self.shipping_city and
                    self.shipping_state and self.shipping_postalcode and
                    self.shipping_country):
                    gc = gmaps.geocode('%s, %s, %s %s-%s, %s' % (
                        self.shipping_street, self.shipping_city,
                        self.shipping_state, self.shipping_postalcode,
                        self.shipping_postalcode, self.shipping_country))
                    if len(gc) == 1:
                        self.shipping_lat = float(
                            gc[0]['geometry']['location']['lat'])
                        self.shipping_lon = float(
                            gc[0]['geometry']['location']['lng'])
            except:
                self.shipping_lat = None
                self.shipping_lon = None

        except:
            self.billing_lat = None
            self.billing_lon = None
            self.shipping_lat = None
            self.shipping_lon = None

        super(Business, self).save()

class BusinessDepartment(models.Model):
    business = models.ForeignKey(Business)
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=255, blank=True)
    active = models.BooleanField(default=False)
    poc = models.ForeignKey('Contact', related_name='business_department_poc', verbose_name='Primary Contact', blank=True, null=True)

    bd_billing_street = models.CharField(max_length=255, blank=True, verbose_name='Billing Street')
    bd_billing_city = models.CharField(max_length=255, blank=True, verbose_name='Billing City')
    bd_billing_state = models.CharField(max_length=2, blank=True, choices=Business.STATES, verbose_name='Billing State')
    bd_billing_postalcode = models.CharField(max_length=32, blank=True, verbose_name='Billing Postal Code')
    bd_billing_mailstop = models.CharField(max_length=16, blank=True, verbose_name='Billing Mailstop')
    bd_billing_country = models.CharField(max_length=128, blank=True, verbose_name='Billing Country')
    bd_billing_lat = models.FloatField(blank=True, null=True, verbose_name='Billing Latitude', help_text='This is automatically set using the Google Maps Geocode API on save.')
    bd_billing_lon = models.FloatField(blank=True, null=True, verbose_name='Billing Longitude', help_text='This is automatically set using the Google Maps Geocode API on save.')

    bd_shipping_street = models.CharField(max_length=255, blank=True, verbose_name='Shipping Street')
    bd_shipping_city = models.CharField(max_length=255, blank=True, verbose_name='Shipping City')
    bd_shipping_state = models.CharField(max_length=2, blank=True, choices=Business.STATES, verbose_name='Shipping State')
    bd_shipping_postalcode = models.CharField(max_length=32, blank=True, verbose_name='Shipping Postal')
    bd_shipping_mailstop = models.CharField(max_length=16, blank=True, verbose_name='Shipping Mailstop')
    bd_shipping_country = models.CharField(max_length=128, blank=True, verbose_name='Shipping Country')
    bd_shipping_lat = models.FloatField(blank=True, null=True, verbose_name='Shipping Latitude', help_text='This is automatically set using the Google Maps Geocode API on save.')
    bd_shipping_lon = models.FloatField(blank=True, null=True, verbose_name='Shipping Longitude', help_text='This is automatically set using the Google Maps Geocode API on save.')

    def __unicode__(self):
        return '%s - %s' % (self.business.short_name, self.name)

    @property
    def billing_street(self):
        if self.bd_billing_street:
            return bd_billing_street
        else:
            return self.business.billing_street

    @property
    def billing_city(self):
        if self.bd_billing_city:
            return bd_billing_city
        else:
            return self.business.billing_city

    @property
    def billing_state(self):
        if self.bd_billing_state:
            return bd_billing_state
        else:
            return self.business.billing_state

    @property
    def billing_postalcode(self):
        if self.bd_billing_postalcode:
            return bd_billing_postalcode
        else:
            return self.business.billing_postalcode

    @property
    def billing_mailstop(self):
        if self.bd_billing_mailstop:
            return bd_billing_mailstop
        else:
            return self.business.billing_mailstop

    @property
    def billing_country(self):
        if self.bd_billing_country:
            return bd_billing_country
        else:
            return self.business.billing_country

    @property
    def billing_lat(self):
        if self.bd_billing_lat:
            return bd_billing_lat
        else:
            return self.business.billing_lat

    @property
    def billing_lon(self):
        if self.bd_billing_lon:
            return bd_billing_lon
        else:
            return self.business.billing_lon

    @property
    def shipping_street(self):
        if self.bd_shipping_street:
            return bd_shipping_street
        else:
            return self.business.shipping_street

    @property
    def shipping_city(self):
        if self.bd_shipping_city:
            return bd_shipping_city
        else:
            return self.business.shipping_city

    @property
    def shipping_state(self):
        if self.bd_shipping_state:
            return bd_shipping_state
        else:
            return self.business.shipping_state

    @property
    def shipping_postalcode(self):
        if self.bd_shipping_postalcode:
            return bd_shipping_postalcode
        else:
            return self.business.shipping_postalcode

    @property
    def shipping_mailstop(self):
        if self.bd_shipping_mailstop:
            return bd_shipping_mailstop
        else:
            return self.business.shipping_mailstop

    @property
    def shipping_country(self):
        if self.bd_shipping_country:
            return bd_shipping_country
        else:
            return self.business.shipping_country

    @property
    def shipping_lat(self):
        if self.bd_shipping_lat:
            return bd_shipping_lat
        else:
            return self.business.shipping_lat

    @property
    def shipping_lon(self):
        if self.bd_shipping_lon:
            return bd_shipping_lon
        else:
            return self.business.shipping_lon

    def save(self):
        try:
            gmaps = googlemaps.Client(
                key=settings.GOOGLE_SERVER_API_KEY,
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET)

            try:
                # geocode billing address
                if (self.bd_billing_street and self.bd_billing_city and
                    self.bd_billing_state and self.bd_billing_postalcode and
                    self.bd_billing_country):
                    gc = gmaps.geocode('%s, %s, %s %s-%s, %s' % (
                        self.bd_billing_street, self.bd_billing_city,
                        self.bd_billing_state, self.bd_billing_postalcode,
                        self.bd_billing_postalcode, self.bd_billing_country))
                    if len(gc) == 1:
                        self.bd_billing_lat = float(
                            gc[0]['geometry']['location']['lat'])
                        self.bd_billing_lon = float(
                            gc[0]['geometry']['location']['lng'])
            except:
                self.bd_billing_lat = None
                self.bd_billing_lon = None

            try:
                # geocode shipping address
                if (self.bd_shipping_street and self.bd_shipping_city and
                    self.bd_shipping_state and self.bd_shipping_postalcode and
                    self.bd_shipping_country):
                    gc = gmaps.geocode('%s, %s, %s %s-%s, %s' % (
                        self.bd_shipping_street, self.bd_shipping_city,
                        self.bd_shipping_state, self.bd_shipping_postalcode,
                        self.bd_shipping_postalcode, self.bd_shipping_country))
                    if len(gc) == 1:
                        self.bd_shipping_lat = float(
                            gc[0]['geometry']['location']['lat'])
                        self.bd_shipping_lon = float(
                            gc[0]['geometry']['location']['lng'])
            except:
                self.bd_shipping_lat = None
                self.bd_shipping_lon = None

        except:
            self.bd_billing_lat = None
            self.bd_billing_lon = None
            self.bd_shipping_lat = None
            self.bd_shipping_lon = None

        super(BusinessDepartment, self).save()

class BusinessNote(models.Model):
    business = models.ForeignKey(Business)
    author = models.ForeignKey(User)
    created_at = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)
    last_edited = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey("self", null=True, blank=True)
    text = models.TextField()

    def get_thread(self, thread):
        thread.append(self)
        for n in BusinessNote.objects.filter(parent=self).order_by('-created_at'):
            thread.append(n.get_thread(), thread)

    def save(self, *args, **kwargs):
        super(BusinessNote, self).save(*args, **kwargs)
        url = '%s%s' % (settings.DOMAIN, reverse('view_business', args=(self.business.id,)))
        # send email to note author and business account owner
        timepiece_emails.business_new_note(self, url)

class BusinessAttachment(MongoAttachment):
    business = models.ForeignKey(Business)

    def __unicode__(self):
        return "%s: %s" % (self.business.short_name, self.filename)

class Contact(models.Model):
    SALUTATIONS = (('mr',  'Mr.'),
                   ('mrs', 'Mrs.'),
                   ('dr',  'Dr.'),
                   ('ms',  'Ms.'),)
    user = models.OneToOneField(User, null=True, blank=True, related_name='contact', on_delete=models.SET_NULL)
    salutation = models.CharField(max_length=8, choices=SALUTATIONS, blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    email = models.CharField(max_length=255, blank=True)
    office_phone = models.CharField(max_length=24, blank=True)
    mobile_phone = models.CharField(max_length=24, blank=True)
    home_phone = models.CharField(max_length=24, blank=True)
    other_phone = models.CharField(max_length=24, blank=True)
    fax = models.CharField(max_length=24, blank=True)

    business = models.ForeignKey(Business, null=True, blank=True)
    business_department = models.ForeignKey(BusinessDepartment, null=True, blank=True)
    assistant = models.ForeignKey('self', null=True, blank=True, help_text='If the assistant is another contact, you can set that here.')
    assistant_name = models.CharField(max_length=255, blank=True)
    assistant_phone = models.CharField(max_length=24, blank=True)
    assistant_email = models.CharField(max_length=255, blank=True)

    mailing_street = models.CharField(max_length=255, blank=True, verbose_name='Mailing Street')
    mailing_city = models.CharField(max_length=255, blank=True, verbose_name='Mailing City')
    mailing_state = models.CharField(max_length=2, blank=True, choices=Business.STATES, verbose_name='Mailing State')
    mailing_postalcode = models.CharField(max_length=32, blank=True, verbose_name='Mailing Postal')
    mailing_mailstop = models.CharField(max_length=16, blank=True, verbose_name='Mailing Mailstop')
    mailing_country = models.CharField(max_length=128, blank=True, verbose_name='Mailing Country')
    mailing_lat = models.FloatField(blank=True, null=True, verbose_name='Mailing Latitude', help_text='This is automatically set using the Google Maps Geocode API on save.')
    mailing_lon = models.FloatField(blank=True, null=True, verbose_name='Mailing Longitude', help_text='This is automatically set using the Google Maps Geocode API on save.')

    other_street = models.CharField(max_length=255, blank=True, verbose_name='Other Street')
    other_city = models.CharField(max_length=255, blank=True, verbose_name='Other City')
    other_state = models.CharField(max_length=2, blank=True, choices=Business.STATES, verbose_name='Other State')
    other_postalcode = models.CharField(max_length=32, blank=True, verbose_name='Other Postal')
    other_mailstop = models.CharField(max_length=16, blank=True, verbose_name='Other Mailstop')
    other_country = models.CharField(max_length=128, blank=True, verbose_name='Other Country')
    other_lat = models.FloatField(blank=True, null=True, verbose_name='Other Latitude', help_text='This is automatically set using the Google Maps Geocode API on save.')
    other_lon = models.FloatField(blank=True, null=True, verbose_name='Other Longitude', help_text='This is automatically set using the Google Maps Geocode API on save.')

    has_opted_out_of_email = models.BooleanField(default=False)
    has_opted_out_of_fax = models.BooleanField(default=False)
    do_not_call = models.BooleanField(default=False)

    birthday = models.DateField(null=True, blank=True)

    lead_source = models.ForeignKey(User, related_name='contact_lead_source')

    tags = TaggableManager()

    class Meta:
        ordering = ('last_name', 'first_name')
        permissions = (
            ('view_contact', 'Can view contact'),
        )

    def __unicode__(self):
      return self.get_name

    def save(self):
        try:
            gmaps = googlemaps.Client(
                key=settings.GOOGLE_SERVER_API_KEY,
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET)

            try:
                # geocode mailing address
                if (self.mailing_street and self.mailing_city and
                    self.mailing_state and self.mailing_postalcode and
                    self.mailing_country):
                    gc = gmaps.geocode('%s, %s, %s %s-%s, %s' % (
                        self.mailing_street, self.mailing_city,
                        self.mailing_state, self.mailing_postalcode,
                        self.mailing_postalcode, self.mailing_country))
                    if len(gc) == 1:
                        self.mailing_lat = float(
                            gc[0]['geometry']['location']['lat'])
                        self.mailing_lon = float(
                            gc[0]['geometry']['location']['lng'])
            except:
                self.mailing_lat = None
                self.mailing_lon = None

            try:
                # geocode other address
                if (self.other_street and self.other_city and
                    self.other_state and self.other_postalcode and
                    self.other_country):
                    gc = gmaps.geocode('%s, %s, %s %s-%s, %s' % (
                        self.other_street, self.other_city,
                        self.other_state, self.other_postalcode,
                        self.other_postalcode, self.other_country))
                    if len(gc) == 1:
                        self.other_lat = float(
                            gc[0]['geometry']['location']['lat'])
                        self.other_lon = float(
                            gc[0]['geometry']['location']['lng'])
            except:
                self.other_lat = None
                self.other_lon = None

        except:
            self.mailing_lat = None
            self.mailing_lon = None
            self.other_lat = None
            self.other_lon = None

        super(Contact, self).save()

    def get_absolute_url(self):
        return reverse('view_contact', args=(self.pk,))

    @property
    def get_notes(self):
        return ContactNote.objects.filter(contact=self).order_by('-created_at')

    @property
    def name(self):
        if self.user:
          return '%s, %s' % (self.user.last_name, self.user.first_name)
        else:
          return '%s, %s' % (self.last_name, self.first_name)

    @property
    def get_name(self):
        if self.user:
          return '%s, %s' % (self.user.last_name, self.user.first_name)
        else:
          return '%s, %s' % (self.last_name, self.first_name)

    @property
    def get_first_name(self):
        if self.user:
            return self.user.first_name
        else:
            return self.first_name

    @property
    def get_last_name(self):
        if self.user:
            return self.user.last_name
        else:
            return self.last_name
    @property
    def get_email(self):
        if self.user:
            return self.user.email
        else:
            return self.email

    @property
    def do_not_call_class(self):
        return "error" if self.do_not_call else ""

class ContactNote(models.Model):
    contact = models.ForeignKey(Contact)
    author = models.ForeignKey(User)
    created_at = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)
    last_edited = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', null=True, blank=True)
    text = models.TextField()

    def get_thread(self, thread):
        thread.append(self)
        for n in ContactNote.objects.filter(parent=self).order_by('-created_at'):
            thread.append(n.get_thread(), thread)

    def save(self, *args, **kwargs):
        super(ContactNote, self).save(*args, **kwargs)
        url = '%s%s' % (settings.DOMAIN, reverse('view_contact', args=(self.contact.id,)))
        # send email to note author and contact lead source
        timepiece_emails.contact_new_note(self, url)


class TrackableProjectManager(models.Manager):

    def get_query_set(self):
        return super(TrackableProjectManager, self).get_query_set().filter(
            status__enable_timetracking=True,
            type__enable_timetracking=True,
        )


class Project(models.Model):
    MINDERS_GROUP_ID = 3

    PROJECT_DEPARTMENTS = Department.DEPARTMENTS

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=12,
        verbose_name="Project Code",
        unique=False,
        blank=True, # this field is required but is manually enforced in the code
        help_text="Auto-generated project code for tracking.")
    ext_code = models.CharField(max_length=255,
        verbose_name="External Project ID",
        unique=False,
        blank=True,
        null=True)
    tracker_url = models.CharField(max_length=255, blank=True, null=False,
            default="", verbose_name="Wiki Url")
    business = models.ForeignKey(Business,
            verbose_name="Company",
            related_name='new_business_projects')
    business_department = models.ForeignKey(BusinessDepartment,
            null=True, blank=True,
            verbose_name="Company Department",
            related_name='new_business_department_projects',
            on_delete=models.SET_NULL)
    client_primary_poc = models.ForeignKey(Contact, blank=True, null=True,
            on_delete=models.SET_NULL)
    point_person = models.ForeignKey(User,
        verbose_name="Minder",
        related_name="minder",
        limit_choices_to={'groups__id__in': settings.TIMEPIECE_BUSINESS_GROUPS},
        help_text="Who is the Project Manager?")
    finder = models.ForeignKey(User,
        limit_choices_to={'groups__id__in': settings.TIMEPIECE_BUSINESS_GROUPS},
        related_name="finder",
        help_text="Who brought in this project?")
    binder =models.ForeignKey(User,
        limit_choices_to={'groups__id__in': settings.TIMEPIECE_BUSINESS_GROUPS},
        related_name="binder",
        help_text="Who is responsible for project/customer follow-up?")
    users = models.ManyToManyField(User, related_name='user_projects',
            through='ProjectRelationship')
    activity_group = models.ForeignKey('entries.ActivityGroup',
            related_name='activity_group', null=True, blank=True,
            verbose_name='restrict activities to',
            on_delete=models.SET_NULL)
    type = models.ForeignKey(Attribute,
            limit_choices_to={'type': 'project-type'},
            related_name='projects_with_type')
    status = models.ForeignKey(Attribute,
            limit_choices_to={'type': 'project-status'},
            related_name='projects_with_status')
    project_department = models.CharField(max_length=16,
      choices=PROJECT_DEPARTMENTS,
      default='other')
    description = models.TextField()
    year = models.SmallIntegerField(blank=True, null=True) # this field is required, but is taken care of in code

    tags = TaggableManager()

    objects = models.Manager()
    trackable = TrackableProjectManager()

    class Meta:
        db_table = 'timepiece_project'  # Using legacy table name.
        ordering = ('code', 'name', 'status', 'type',)
        permissions = (
            ('view_project', 'Can view project'),
            ('email_project_report', 'Can email project report'),
            ('view_project_time_sheet', 'Can view project time sheet'),
            ('export_project_time_sheet', 'Can export project time sheet'),
            ('generate_project_invoice', 'Can generate project invoice'),
        )

    def __unicode__(self):
        return '{0}: {1}'.format(self.code, self.name)

    def delete(self, *args, **kwargs):
        try:
            # we need to delete the associate wiki to free up the slug
            urlpath = URLPath.objects.get(slug=self.code)
            urlpath.delete()
        except:
            pass

        return super(Project, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        # if this is a CREATE, create Project Code
        if self.id is None:
            print 'got to there'
            # get the current year, if year not provided
            if not self.year:
                self.year = datetime.datetime.now().year
            print 'year', self.year
            # determine the project counter incrementer and create unique code
            proj_count = Project.objects.filter(business=self.business, year=self.year).count() + 1
            print 'proj_count', proj_count
            self.code = '%s-%s-%03d' % (self.business.short_name, str(self.year)[2:], proj_count)
            print 'code', self.code

            # create new wiki
            try:
                project_parent = URLPath.objects.get(id=settings.WIKI_PROJECT_ID)
                wiki_path = URLPath.create_article(project_parent,
                                self.code,
                                site=Site.objects.get(id=settings.SITE_ID),
                                title='%s: %s' % (self.code, self.name),
                                article_kwargs={'owner': self.point_person},
                                content='This is base article for the project %s: %s.' % (self.code, self.name),
                            )
                self.tracker_url = '/wiki/' + str(wiki_path)
            except:
                print sys.exc_info(), traceback.format_exc()
                pass

        super(Project, self).save(*args, **kwargs)
        minders = Group.objects.get(id=self.MINDERS_GROUP_ID)
        for u in User.objects.filter(id__in=Project.objects.all().values('point_person')):
            # add user to Minders group
            u.groups.add(minders)

    @property
    def get_attachments(self):
        return ProjectAttachment.objects.filter(project=self).order_by('filename')

    @property
    def billable(self):
        return self.type.billable

    def get_absolute_url(self):
        return reverse('view_project', args=(self.pk,))

    def get_active_contracts(self):
        """Returns all associated contracts which are not marked complete."""
        ProjectContract = get_model('contracts', 'ProjectContract')
        return self.contracts.exclude(status=ProjectContract.STATUS_COMPLETE)

    @property
    def milestones(self):
        return Milestone.objects.filter(project=self)

    @property
    def activity_goals(self):
        return ActivityGoal.objects.filter(project=self).order_by(
          'employee__last_name', 'employee__first_name', 'goal_hours',)

    @property
    def open_general_tasks(self):
        return self.generaltask_set.filter(status__terminal=False).order_by(
          'status__terminal', '-created_at')

    @property
    def pending_milestones(self):
        return self.milestone_set.filter(
            status__in=[Milestone.NEW, Milestone.MODIFIED])


class RelationshipType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255)

    class Meta:
        db_table = 'timepiece_relationshiptype'  # Using legacy table name.

    def __unicode__(self):
        return self.name


class ProjectRelationship(models.Model):
    types = models.ManyToManyField(RelationshipType, blank=True,
        related_name='project_relationships')
    user = models.ForeignKey(User, related_name='project_relationships')
    project = models.ForeignKey(Project, related_name='project_relationships')

    class Meta:
        db_table = 'timepiece_projectrelationship'  # Using legacy table name.
        unique_together = ('user', 'project')

    def __unicode__(self):
        return "{project}'s relationship to {user}".format(
            project=self.project.name,
            user=self.user.get_name_or_username(),
        )

class ProjectAttachment(models.Model):
    project = models.ForeignKey(Project)
    bucket = models.CharField(max_length=64)
    uuid = models.TextField() # AWS S3 uuid
    filename = models.CharField(max_length=128)
    upload_datetime = models.DateTimeField(auto_now_add=True)
    uploader = models.ForeignKey(User)
    description = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return "%s: %s" % (self.project, self.filename)

    def get_download_url(self):
        conn = boto.connect_s3(settings.AWS_UPLOAD_CLIENT_KEY,
            settings.AWS_UPLOAD_CLIENT_SECRET_KEY)
        bucket = conn.get_bucket(self.bucket)
        s3_file_path = bucket.get_key(self.uuid)
        url = s3_file_path.generate_url(expires_in=15) # expiry time is in seconds
        return url

class Milestone(models.Model):
    NEW = 'new'
    MODIFIED = 'modified'
    APPROVED = 'approved'
    DENIED = 'denied'
    STATUSES = ((NEW, 'New'),
                (MODIFIED, 'Modified'),
                (APPROVED, 'Approved'),
                (DENIED, 'Denied'))

    project = models.ForeignKey(Project)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    author = models.ForeignKey(User, related_name='milestone_author')
    created = models.DateTimeField(auto_now_add=True)
    editor = models.ForeignKey(User, related_name='milestone_editor')
    modified = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=8, choices=STATUSES, default=NEW)
    approver = models.ForeignKey(User, related_name='milestone_approver',
        null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return '%s: %s' % (self.project.code, self.name)

    class Meta:
        ordering = ('due_date', 'name')
        permissions = (('approve_milestone', 'Can approve milestone'),)

    @property
    def approved(self):
        return self.status == self.APPROVED

    @property
    def denied(self):
        return self.status == self.DENIED

    @property
    def get_notes(self):
        return self.milestonenote_set.all()

    @property
    def previous_approval(self):
        if len(self.approvals.all()):
            return self.approvals.all().order_by('-approval_date')[0]
        else:
            return None


class ApprovedMilestone(models.Model):
    milestone = models.ForeignKey(Milestone, related_name="approvals")
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    author = models.ForeignKey(User, related_name='approved_milestone_author')
    created = models.DateTimeField()
    editor = models.ForeignKey(User, related_name='approved_milestone_editor')
    modified = models.DateTimeField()
    status = models.CharField(max_length=8, choices=Milestone.STATUSES,
        default=Milestone.APPROVED)
    approver = models.ForeignKey(User,
        related_name='approved_milestone_approver',
        null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('project__code', 'milestone', '-approval_date')

    def __unicode__(self):
        return '%s approval' % (str(self.milestone))


class MilestoneNote(models.Model):
    milestone = models.ForeignKey(Milestone)
    text = models.TextField()
    author = models.ForeignKey(User, related_name='authored_milestone_notes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['milestone', '-created_at']

    def __unicode__(self):
        return '%s note' % (str(self.milestone))


from timepiece.entries.models import Entry, Activity
class ActivityGoal(models.Model):
    milestone = models.ForeignKey(Milestone, null=True, blank=True)
    project = models.ForeignKey(Project, null=True, blank=True)
    activity = models.ForeignKey(Activity, null=True, blank=True, help_text='Review <a href="/timepiece/activity/cheat-sheet" target="_blank">this reference</a> for guidance on activities.')
    goal_hours = models.DecimalField(max_digits=7, decimal_places=2)
    employee = models.ForeignKey(User, related_name='activity_goals', null=True, blank=True)
    date = models.DateField(null=True, blank=True, verbose_name='Start Date')
    end_date = models.DateField(verbose_name='End Date')

    def __unicode__(self):
        return '%s: %s - %s (%s)' % (self.project.code,
            self.activity, self.employee, self.goal_hours)

    class Meta:
        ordering = ('project__code', 'employee__last_name', 'employee__first_name', 'goal_hours',)

    def clean(self):
        # ensure that the end_date is after the date
        if type(self.date) is not datetime.date:
          raise ValidationError('Select a Start Date.')

        if type(self.end_date) is not datetime.date:
          raise ValidationError('Select an End Date.')

        if self.date > self.end_date:
            raise ValidationError('The Start Date cannot come after the '
                'End Date.')

    @property
    def get_charged_hours(self):
        return Entry.objects.filter(
            project=self.project,
            activity=self.activity,
            start_time__gte=datetime.datetime.combine(
                self.date, datetime.time.min),
            end_time__lte=datetime.datetime.combine(
                self.end_date, datetime.time.max),
            user=self.employee
            ).aggregate(Sum('hours'))['hours__sum'] or Decimal('0.0')

    @property
    def get_percent_complete(self):
        if self.goal_hours == Decimal('0.0'):
            return 100.
        else:
            return 100.*(float(self.get_charged_hours) / float(self.goal_hours))

    @property
    def get_remaining_hours(self):
        return self.goal_hours - self.get_charged_hours

    @property
    def goal_overrun(self):
        return self.get_remaining_hours < 0

    @property
    def current(self):
        return self.end_date >= datetime.date.today()




class Lead(models.Model):
    STATUS_OPEN = '0-open'
    STATUS_CONTACTING = '1-contacting'
    STATUS_CONTACTED = '2-contacted'
    STATUS_BAD_INFO = '3-bad-info'
    STATUS_NO_RESPONSE = '4-no-response'
    STATUS_QUALIFIED = '5-qualified'
    STATUS_GARDEN = '6-garden'
    STATUS_UNQUALIFIED = '7-unqualified'
    STATUS_COMPLETE = '8-complete'
    STATUSES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_CONTACTING, 'Contacting'),
        (STATUS_CONTACTED, 'Contacted'),
        (STATUS_BAD_INFO, 'Bad Information'),
        (STATUS_NO_RESPONSE, 'No Response'),
        (STATUS_QUALIFIED, 'Qualified'),
        (STATUS_GARDEN, 'Garden'),
        (STATUS_UNQUALIFIED, 'Unqualified'),
        (STATUS_COMPLETE, 'Complete'),
    ]

    title = models.CharField(max_length=64,
        help_text='Provide a name or title to identify the lead.')
    status = models.CharField(max_length=16,
        default=STATUS_OPEN, choices=STATUSES)
    lead_source = models.ForeignKey(User, related_name='lead_source',
        limit_choices_to={'groups':1})
    aac_poc = models.ForeignKey(User, related_name='lead_poc',
        verbose_name='AAC Primary',
        limit_choices_to={'groups':1, 'is_active':True})
    primary_contact = models.ForeignKey(Contact,
        verbose_name='Primary Contact', blank=True, null=True,
        help_text=('Search for a Contact to select as the Primary Contact '
        'for this lead.  If the contact is not yet in the Contact database, '
        '<a href="/timepiece/contact/create" target="_blank">add</a> them '
        'first.  If a contact is not yet identified, you can select '
        'a Business instead.'))
    business_placeholder = models.ForeignKey(Business, verbose_name='Business',
        blank=True, null=True,
        help_text=('If a Primary Contact has not yet been identified, select '
        'the Business this lead is associated with.  Once a Contact is '
        'identified, this field will be ignored.  If the business is not yet '
        'in the Business database, <a href="/timepiece/business/create" '
        'target="_blank">add</a> it first.'))
    contacts = models.ManyToManyField(Contact, null=True, blank=True,
        related_name='lead_contacts', verbose_name='Other Contacts')

    created_by = models.ForeignKey(User, related_name='lead_created_by')
    last_editor = models.ForeignKey(User, related_name='lead_edited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    tags = TaggableManager()

    class Meta:
        ordering = ['status', 'title']

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('view_lead', args=(self.id,))

    @property
    def get_notes(self):
        return LeadNote.objects.filter(lead=self).order_by('-created_at')

    @property
    def get_attachments(self):
        return LeadAttachment.objects.filter(lead=self)

    @property
    def get_opportunities(self):
        return self.opportunity_set.all().order_by('title')

    @property
    def get_projects(self):
       pl = [proj for opps in self.get_opportunities for proj in opps.project.all()]
       return set(pl)

    @property
    def open_general_tasks(self):
        return self.generaltask_set.all() # status__terminal=False

    def save(self, *args, **kwargs):
        make_history = True
        if self.pk is not None:
            orig = Lead.objects.get(pk=self.pk)
            if orig.status == self.status:
                make_history = False

        super(Lead, self).save(*args, **kwargs)

        if make_history:
            history = LeadHistory(lead=self,status=self.status)
            history.save()

class LeadAttachment(MongoAttachment):
    lead = models.ForeignKey(Lead)

    def __unicode__(self):
        return "%s: %s" % (self.lead, self.filename)

class LeadNote(models.Model):
    lead = models.ForeignKey(Lead)
    author = models.ForeignKey(User)
    created_at = models.DateTimeField(auto_now_add=True)
    edited = models.BooleanField(default=False)
    last_edited = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', null=True, blank=True)
    text = models.TextField()

    def get_thread(self, thread):
        thread.append(self)
        for n in LeadNote.objects.filter(parent=self).order_by('-created_at'):
            thread.append(n.get_thread(), thread)

    def save(self, *args, **kwargs):
        super(LeadNote, self).save(*args, **kwargs)
        url = '%s%s' % (settings.DOMAIN, reverse('view_lead', args=(self.lead.id,)))
        # send email to lead aac primary poc
        timepiece_emails.lead_new_note(self, url)

class LeadHistory(models.Model):
    lead = models.ForeignKey(Lead)
    status = models.CharField(max_length=16,choices=Lead.STATUSES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering=['-created_at']

    def __unicode__(self):
        return '%s - %s (%s)' % (self.lead, self.status, self.created_at)


class DistinguishingValueChallenge(models.Model):
    lead = models.ForeignKey(Lead, blank=True, null=True)
    business = models.ForeignKey(Business, blank=True, null=True)
    order = models.PositiveSmallIntegerField(help_text='Define order/priority of this DV.')
    probing_question = models.TextField(blank=True, help_text='Provide a probing question that could be used in a conversation with a potential client.')
    description = models.TextField(blank=True, help_text='Have the potential customer describe the pain/challenge.')
    short_name = models.CharField(max_length=32, blank=True, help_text='Provide a short identifying name for this DV.')
    longevity = models.TextField(blank=True, help_text='How long have you been facing this pain/challenge?')
    start_date = models.DateField(blank=True, null=True, help_text='Based on the response to the above question, estimate the date when the pain/challenge started.')
    steps = models.TextField(blank=True, help_text='What steps have you already taken to overcome it?')
    results = models.TextField(blank=True, help_text='What were the results from the steps already taken?')
    due = models.TextField(blank=True, help_text='Do you have a specific timeline for overcoming this pain/challenge?')
    due_date = models.DateField(blank=True, null=True, help_text='If possible, set a specific date for the timeline described above.')
    cost = models.TextField(blank=True, help_text='What do you estimate this challenges costs you (in time or money) each month?')
    confirm_resources = models.BooleanField(blank=True, default=False, help_text='Have you confirmed that AAC Engineering has adequate resources to support the proposed project? (Contact the Operations Manager.)')
    resources_notes = models.TextField(blank=True, help_text='Optionally add notes on the available resources.')
    benefits_begin = models.TextField(blank=True, help_text='When do you expect benefits from the project execution to begin?')
    date_benefits_begin = models.DateField(blank=True, null=True, help_text='If possible, set a specific date for when benefits are to begin.')
    confirm = models.BooleanField(blank=True, default=False, help_text='Confirm Evaluation and Decision Process.')
    confirm_notes = models.TextField(blank=True, help_text='Optionally add notes on the confirmation.')
    commitment = models.BooleanField(blank=True, default=False, help_text='Commitment: Agree on clear outcomes.')
    commitment_notes = models.TextField(blank=True, help_text='Optionally add notes on the commitment.')
    last_activity = models.DateTimeField(auto_now=True)
    closed = models.BooleanField(default=False, help_text='Check this box once this DV is resolved and/or closed.')

    class Meta:
        ordering = ['order', '-due_date']
        verbose_name = 'Differentiating Value'
        verbose_name_plural = 'Differentiating Values'

    def __unicode__(self):
        return '%s - DV - %s' % (self.lead, self.short_name)

    def save(self, *args, **kwargs):
        if self.id is None:
            self.order = self.lead.distinguishingvaluechallenge_set.count() + 1
        if len(self.short_name) == 0:
            self.short_name = 'DV %d' % self.order

        return super(DistinguishingValueChallenge, self).save(*args, **kwargs)

    def tab_name(self):
        return 'dvc%d' % (list(self.lead.distinguishingvaluechallenge_set.all()
            ).index(self) + 1)

    @property
    def get_cost_items(self):
        return DVCostItem.objects.filter(dv=self)

    @property
    def get_cost(self):
        cost = Decimal('0.0')
        for ci in DVCostItem.objects.filter(dv=self):
            cost += ci.get_cost
        return cost

class DVCostItem(models.Model):
    dv = models.ForeignKey(DistinguishingValueChallenge)
    description = models.CharField(max_length=64,
        help_text='Provide a summary description of the cost line item.')
    details = models.TextField(blank=True,
        help_text='Optionally add more details about this cost item.  You can reference an attachmen here as well.')
    cost = models.DecimalField(max_digits=11, decimal_places=2,
        null=True, blank=True,
        help_text='Either set a cost or define man hours and rate below.')
    man_hours = models.DecimalField(max_digits=11, decimal_places=2,
        null=True, blank=True, verbose_name='Man Hours')
    rate = models.DecimalField(max_digits=6, decimal_places=2,
        verbose_name='Houlry Rate', null=True, blank=True)

    class Meta:
        ordering = ['description']

    def __unicode__(self):
        return '%s - %s - %f' % (self.dv, self.description,
            float(self.get_cost))

    @property
    def get_cost(self):
        if self.cost:
            return self.cost
        else:
            return self.man_hours * self.rate

    @property
    def cost_explanation(self):
        if self.cost:
            return 'Direct cost estimate.'
        else:
            return 'Labor cost of %.2f hours at $%.2f per hour.' % (
                self.man_hours, self.rate)

    def clean(self):
        # ensure that either a cost is provided or a combination of Man Hours and Rate
        if self.cost is None:
            if self.man_hours is None or self.rate is None:
                raise ValidationError('You must set either a direct Cost '
                    'or both Man Hours and Hourly Rate.')
        else:
            if self.man_hours or self.rate:
                raise ValidationError('If you set a direct Cost, you '
                    'cannot also set both Man Hours and an Hourly Rate.')

class TemplateDifferentiatingValue(models.Model):
    short_name = models.CharField(max_length=32, help_text='Provide a short identifying name for this Template DV.')
    probing_question = models.TextField(help_text='Provide a probing question that could be used in a conversation with a potential client.')

    class Meta:
        ordering = ['short_name']

    def __unicode__(self):
        return self.short_name

class Opportunity(models.Model):
    PROPOSAL_STATUSES = (
        ('0-in-progress', 'In Progress'),
        ('1-submitted', 'Submitted'),
        ('2-counter', 'Counter Received'),
        ('3-accepted', 'Accepted'),
        ('4-cancelled', 'Cancelled'),
        ('5-declined', 'Declined')
    )
    title = models.CharField(max_length=128,
        help_text='Provide a name for the Opportunity (or name of the associated proposal).')
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    lead = models.ForeignKey(Lead)
    differentiating_value = models.ForeignKey(DistinguishingValueChallenge, null=True, blank=True,
        help_text='If the Opportunity started as a Lead\'s Differentiating Value, associate it here.')
    proposal = models.ForeignKey(LeadAttachment, null=True, blank=True,
        help_text='After uploading the proposal as an attachment to the Lead, associate the proposal with this Opportunity.')
    proposal_status = models.CharField(max_length=16, default='in-progress', choices=PROPOSAL_STATUSES)
    proposal_status_date = models.DateTimeField(auto_now_add=True,
        help_text='Timestamp for when the proposal status was set.')
    project = models.ManyToManyField(Project, null=True, blank=True,
        help_text='If this Opportunity results in a project, identify the project(s) here.')

    @property
    def get_status_class(self):
        CLASSES = {'0-in-progress': '',
                   '1-submitted': 'label-info',
                   '2-counter': 'label-warning',
                   '3-accepted': 'label-success',
                   '4-cancelled': 'label-inverse',
                   '5-declined': 'label-important'}

        return CLASSES[self.proposal_status]

    def update_status(self, status):
        """Updates the status of the Opportunity's proposal and sets the
        associated timestamp.
        """

        self.status = status
        self.proposal_status_date = datetime.datetime.now()
        self.save()
