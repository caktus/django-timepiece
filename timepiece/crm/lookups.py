from collections import namedtuple

from django.contrib.auth.models import User
from django.utils.safestring import mark_safe

from selectable.base import LookupBase
from selectable.base import ModelLookup
from selectable.registry import registry

from timepiece.crm.models import Project, Business


class ProjectLookup(ModelLookup):
    model = Project
    search_fields = ('name__icontains', 'business__name__icontains',
                     'business__short_name__icontains')

    def get_item_label(self, project):
        return mark_safe(u'<span class="project">%s</span>' % self.get_item_value(project))

    def get_item_value(self, project):
        return project.name if project else ''


class BusinessLookup(ModelLookup):
    model = Business
    search_fields = ('name__icontains', 'short_name__icontains')

    def get_item_label(self, business):
        return mark_safe(u'<span class="business">%s</span>' % self.get_item_value(business))

    def get_item_value(self, business):
        return business.name if business else ''


class UserLookup(ModelLookup):
    model = User
    search_fields = ('username__icontains', 'first_name__icontains',
                     'last_name__icontains', 'email__icontains')

    def get_query(self, request, q):
        return super(UserLookup, self).get_query(request, q).order_by('last_name')

    def get_item_label(self, user):
        return mark_safe(u'<span class="user">%s</span>' % self.get_item_value(user))

    def get_item_value(self, user):
        return user.get_name_or_username() if user else ''


class QuickLookup(LookupBase):

    def __init__(self, *args, **kwargs):
        self.lookups = {
            'user': UserLookup(),
            'project': ProjectLookup(),
            'business': BusinessLookup(),
        }
        super(QuickLookup, self).__init__(*args, **kwargs)

    def get_query(self, request, q):
        results = []
        SearchResult = namedtuple('SearchResult', ['result_type', 'item', 'label', 'value'])

        for result_type, lookup in self.lookups.items():
            for item in lookup.get_query(request, q)[:10]:
                label = lookup.get_item_label(item)
                value = lookup.get_item_value(item)
                results.append(SearchResult(result_type, item, label, value))

        results.sort(key=lambda a: a.value)
        return results

    def get_item_label(self, item):
        return item.label

    def get_item_id(self, item):
        return '{0}-{1}'.format(item.result_type, item.item.pk)

    def get_item(self, value):
        try:
            result_type, pk = value.split('-', 1)
            return self.lookups[result_type].get_item(pk)
        except (ValueError, KeyError):
            return None

    def get_item_value(self, item):
        return item.value if item else ''


registry.register(BusinessLookup)
registry.register(ProjectLookup)
registry.register(UserLookup)
registry.register(QuickLookup)
