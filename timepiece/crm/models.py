from django.contrib.auth.models import User, Group
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import get_model, Sum, Q
import datetime
import sys, traceback
from decimal import Decimal
from itertools import groupby
from timepiece.utils import get_active_entry

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
    hours_per_week = models.DecimalField(max_digits=8, decimal_places=2,
            default=40)
    business = models.ForeignKey('Business')
    employee_type = models.CharField(max_length=24, choices=EMPLOYEE_TYPES.items(), default=INACTIVE)
    earns_pto = models.BooleanField(default=True, help_text='Does the employee earn Paid Time Off?')
    hire_date = models.DateField(blank=True, null=True)

    class Meta:
        db_table = 'timepiece_userprofile'  # Using legacy table name.

    def __unicode__(self):
        return unicode(self.user)

    @property
    def get_pto(self):
        pto = PaidTimeOffLog.objects.filter(
            user_profile=self).aggregate(Sum('amount'))['amount__sum']
        if pto:
            return pto
        else:
            return Decimal('0.0')


class PaidTimeOffRequest(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    DENIED = 'denied'
    PROCESSED = 'processed'
    STATUSES = {
        PENDING: 'Pending',
        APPROVED: 'Approved',
        DENIED: 'Denied',
        PROCESSED: 'Processed',
    }
    user_profile = models.ForeignKey(UserProfile, verbose_name='Employee')
    request_date = models.DateTimeField(auto_now_add=True)
    pto = models.BooleanField(verbose_name='Select for Paid Time Off (Unselect for Unpaid Time Off)', default=True, help_text='Is the request for Paid Time Off (checked) or Unpaid Time Off (unchecked)?')
    pto_start_date = models.DateField(verbose_name='Time Off Start Date', blank=True, null=True)
    pto_end_date = models.DateField(verbose_name='Time Off End Date', blank=True, null=True)
    amount = models.DecimalField(verbose_name='Number of Hours', max_digits=7, decimal_places=2)
    comment = models.TextField(verbose_name='Reason / Description', blank=True)
    approval_date = models.DateTimeField(blank=True, null=True)
    approver = models.ForeignKey(User, related_name='pto_approver', blank=True, null=True)
    process_date = models.DateTimeField(blank=True, null=True)
    processor = models.ForeignKey(User, related_name='pto_processor', blank=True, null=True)
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
    pto_request = models.ForeignKey(PaidTimeOffRequest, blank=True, null=True)

    class Meta:
        ordering = ('user_profile', '-date',)

    def __unicode__(self):
        return '%s %s %f' % (self.user_profile, str(self.date), float(self.amount))


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
              ('IL', 'Illinoi'),
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
    short_name = models.CharField(max_length=255, blank=True)
    #email = models.EmailField(blank=True)
    poc = models.ForeignKey(User, related_name='business_poc', verbose_name='Primary Contact')
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    external_id = models.CharField(max_length=32, blank=True)

    classification = models.CharField(max_length=8, blank=True, choices=BIZ_CLASS)
    active = models.BooleanField(default=False)
    status = models.CharField(max_length=16, null=True, blank=True, choices=BIZ_STATUS)
    account_owner = models.ForeignKey(User, blank=True, null=True, related_name='biz_account_holder')
    
    billing_street = models.CharField(max_length=255, blank=True)
    billing_city = models.CharField(max_length=255, blank=True)
    billing_state = models.CharField(max_length=2, blank=True, choices=STATES)
    billing_postalcode = models.CharField(max_length=32, blank=True)
    billing_mailstop = models.CharField(max_length=16, blank=True)
    billing_country = models.CharField(max_length=128, blank=True)
    billing_lat = models.FloatField(blank=True, null=True, verbose_name='Billing Latitude', help_text='This is automatically set using the Google Maps Geocode API on save.')
    billing_lon = models.FloatField(blank=True, null=True, verbose_name='Billing Longitude', help_text='This is automatically set using the Google Maps Geocode API on save.')

    shipping_street = models.CharField(max_length=255, blank=True)
    shipping_city = models.CharField(max_length=255, blank=True)
    shipping_state = models.CharField(max_length=2, blank=True, choices=STATES)
    shipping_postalcode = models.CharField(max_length=32, blank=True)
    shipping_mailstop = models.CharField(max_length=16, blank=True)
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
    def get_departments(self):
        return BusinessDepartment.objects.filter(business=self).order_by('short_name')

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

    def __unicode__(self):
        return self.name

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


# class Contact(models.Model):
#     user = models.ForeignKey(User, null=True, blank=True)
#     first_name = models.CharField(max_length=255, blank=True)
#     last_name = models.CharField(max_length=255, blank=True)
#     email = models.CharField(max_length=255, blank=True)
#     office = models.CharField(max_length=16, blank=True)
#     mobile = models.CharField(max_length=16, blank=True)
#     fax = models.CharField(max_length=16, blank=True)
#     business = model.ForeignKey(Business, null=True, blank=True)
#     business_department = model.ForeignKey(BusinessDepartment, null=True, blank=True)

#     @property
#     def get_name(self):
#         if self.user:
#             return str(self.user)
#         else:
#             return '%s %s' % (self.first_name, self.last_name)

#     @property
#     def get_first_name(self):
#         if self.user:
#             return self.user.first_name
#         else:
#             return self.first_name

#     @property
#     def get_last_name(self):
#         if self.user:
#             return self.user.last_name
#         else:
#             return self.last_name


class TrackableProjectManager(models.Manager):

    def get_query_set(self):
        return super(TrackableProjectManager, self).get_query_set().filter(
            status__enable_timetracking=True,
            type__enable_timetracking=True,
        )


class Project(models.Model):
    MINDERS_GROUP_ID = 3

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=12,
        verbose_name="Project Code",
        unique=False,
        blank=True, # this field is required but is manually enforced in the code
        help_text="Auto-generated project code for tracking.")
    tracker_url = models.CharField(max_length=255, blank=True, null=False,
            default="", verbose_name="Wiki Url")
    business = models.ForeignKey(Business,
            verbose_name="Company",
            related_name='new_business_projects')
    business_department = models.ForeignKey(BusinessDepartment,
            null=True, blank=True,
            verbose_name="Company Department",
            related_name='new_business_department_projects')
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
            verbose_name='restrict activities to')
    type = models.ForeignKey(Attribute,
            limit_choices_to={'type': 'project-type'},
            related_name='projects_with_type')
    status = models.ForeignKey(Attribute,
            limit_choices_to={'type': 'project-status'},
            related_name='projects_with_status')
    description = models.TextField()
    year = models.SmallIntegerField(blank=True, null=True) # this field is required, but is taken care of in code

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

    def save(self, *args, **kwargs):
        # if this is a CREATE, create Project Code
        if self.id is None:
            print 'got to there'
            # get the current year, if year not provided
            if not self.year:
                self.year = datetime.datetime.now().year

            # determine the project counter incrementer and create unique code
            proj_count = Project.objects.filter(business=self.business, year=self.year).count() + 1
            self.code = '%s-%s-%03d' % (self.business.short_name, str(self.year)[2:], proj_count)

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


class Milestone(models.Model):
    project = models.ForeignKey(Project)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_date = models.DateField()

    def __unicode__(self):
        return '%s: %s' % (self.project.code, self.name)

    @property
    def activity_goals(self):
        return ActivityGoal.objects.filter(milestone=self)

    class Meta:
        ordering = ('due_date',)


from timepiece.entries.models import Activity
class ActivityGoal(models.Model):
    milestone = models.ForeignKey(Milestone)
    activity = models.ForeignKey(Activity, null=True, blank=True, help_text='Review <a href="/timepiece/activity/cheat-sheet" target="_blank">this reference</a> for guidance on activities.')
    goal_hours = models.DecimalField(max_digits=7, decimal_places=2)
    employee = models.ForeignKey(User, related_name='activity_goals', null=True, blank=True)
    date = models.DateField(null=True, blank=True)

    def __unicode__(self):
        if self.employee:
            return '%s: %s - %s (%s)' % (self.milestone, 
                self.activity, self.employee, self.goal_hours)
        else:
            return '%s: %s - %s (%s)' % (self.milestone, 
                self.activity, 'n/a', self.goal_hours)

    class Meta:
        ordering = ('milestone', 'employee__last_name', 'goal_hours',)
