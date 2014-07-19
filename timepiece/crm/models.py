from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import get_model

from timepiece.utils import get_active_entry


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
    user = models.OneToOneField(User, unique=True, related_name='profile')
    hours_per_week = models.DecimalField(max_digits=8, decimal_places=2,
            default=40)
    business = models.ForeignKey('Business')

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
        if self.short_name:
            return '%s: %s' % (self.short_name, self.name)
        else:
            return self.name


class TrackableProjectManager(models.Manager):

    def get_query_set(self):
        return super(TrackableProjectManager, self).get_query_set().filter(
            status__enable_timetracking=True,
            type__enable_timetracking=True,
        )


class Project(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=12,
        verbose_name="Project Code",
        unique=False,
        help_text="Auto-generated project code for tracking.")
    tracker_url = models.CharField(max_length=255, blank=True, null=False,
            default="", verbose_name="Wiki Url")
    business = models.ForeignKey(Business,
            verbose_name="Company",
            related_name='new_business_projects')
    point_person = models.ForeignKey(User,
        verbose_name="Minder",
        related_name="minder",
        limit_choices_to={'groups__id': 1},
        help_text="Who is the Project Manager?")
    finder = models.ForeignKey(User,
        limit_choices_to={'groups__id': 1},
        related_name="finder",
        help_text="Who brought in this project?")
    binder =models.ForeignKey(User,
        limit_choices_to={'groups__id': 1},
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
        return '{0} {1}'.format(self.code, self.name)

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
