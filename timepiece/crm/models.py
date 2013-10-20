from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import get_model


# Add a utility method to the User class that will tell whether or not a
# particular user has any unclosed entries
User.clocked_in = property(lambda user: user.timepiece_entries.filter(
    end_time__isnull=True).count() > 0)


# Utility method to get user's name, falling back to username.
User.get_name_or_username = lambda user: user.get_full_name() or user.username


User.get_absolute_url = lambda user: reverse('view_user', args=(user.pk,))


User.get_timesheet_url = lambda user: reverse('view_user_timesheet', args=(user.pk,))


class UserProfile(models.Model):
    user = models.OneToOneField(User, unique=True, related_name='profile')
    hours_per_week = models.DecimalField(max_digits=8, decimal_places=2,
            default=40)

    class Meta:
        db_table = 'timepiece_userprofile'  # Using legacy table name.

    def __unicode__(self):
        return unicode(self.user)


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
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    external_id = models.CharField(max_length=32, blank=True)

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
        return self.short_name or self.name


class TrackableProjectManager(models.Manager):

    def get_query_set(self):
        return super(TrackableProjectManager, self).get_query_set().filter(
            status__enable_timetracking=True,
            type__enable_timetracking=True,
        )


class Project(models.Model):
    name = models.CharField(max_length=255)
    tracker_url = models.CharField(max_length=255, blank=True, null=False,
            default="")
    business = models.ForeignKey(Business,
            related_name='new_business_projects')
    point_person = models.ForeignKey(User, limit_choices_to={'is_staff': True})
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

    objects = models.Manager()
    trackable = TrackableProjectManager()

    class Meta:
        db_table = 'timepiece_project'  # Using legacy table name.
        ordering = ('name', 'status', 'type',)
        permissions = (
            ('view_project', 'Can view project'),
            ('email_project_report', 'Can email project report'),
            ('view_project_time_sheet', 'Can view project time sheet'),
            ('export_project_time_sheet', 'Can export project time sheet'),
            ('generate_project_invoice', 'Can generate project invoice'),
        )

    def __unicode__(self):
        return '{0} ({1})'.format(self.name, self.business.get_display_name())

    @property
    def billable(self):
        return self.type.billable

    def get_absolute_url(self):
        return reverse('view_project', args=(self.pk,))

    def get_active_contracts(self):
        """Returns all associated contracts which are not marked complete."""
        ProjectContract = get_model('contracts', 'ProjectContract')
        return self.contracts.exclude(status=ProjectContract.STATUS_COMPLETE)


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
