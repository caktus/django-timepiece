from django.db.models import Q
from django.core.urlresolvers import reverse
from django.contrib.auth import models as auth_models

from selectable.base import ModelLookup
from selectable.base import LookupBase
from selectable.registry import registry

from timepiece import models as timepiece


class ProjectLookup(ModelLookup):
    model = timepiece.Project
    search_fields = ('name__icontains',)
registry.register(ProjectLookup)

class UserLookup(LookupBase):
    def get_query(self, request, q):
        """
        return a query set.  you also have access to request.user if needed
        """
        return auth_models.User.objects.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        ).select_related().order_by('last_name')[:10]

    def format_item(self, user):
        """
        simple display of an object when it is displayed in the list of
        selected objects
        """
        return unicode(user)

    def format_result(self, user):
        """
        a more verbose display, used in the search results display.
        may contain html and multi-lines
        """
        return u"<span class='individual'>%s %s</span>" % \
        (user.first_name, user.last_name)

    def get_objects(self, ids):
        """
        given a list of ids, return the objects ordered as you would like them
        on the admin page. This is for displaying the currently selected items
        (in the case of a ManyToMany field)
        """
        return auth_models.User.objects.filter(pk__in=ids)


class SearchResult(object):
    """
    Fake search result for concatenating search queries.
    """
    def __init__(self, pk, type, name):
        self.pk = "%s-%d" % (type, pk)
        self.type = type
        self.name = name


class QuickLookup(LookupBase):
    def get_query(self, request, q):
        """
        return a query set (or a fake one).  you also have access to
        request.user if needed
        """
        results = []
        
        users = auth_models.User.objects.filter(
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        ).select_related().order_by('last_name')[:10]

        for user in users:
            name = user.get_full_name()
            results.append(
                SearchResult(user.pk, 'individual', name)
            )

        projects = timepiece.Project.objects.filter(
            name__icontains=q,
        ).select_related()[:10]

        for project in projects:
            results.append(
                SearchResult(project.pk, 'project', project.name)
            )

        businesses = timepiece.Business.objects.filter(
            name__icontains=q,
        ).select_related()[:10]

        for business in businesses:
            results.append(
                SearchResult(business.pk, 'business', business.name)
            )
        
        results.sort(lambda a, b: cmp(a.name, b.name))
        return results

    '''def format_item(self, item):
        """
        simple display of an object when it is displayed in the list of
        selected objects
        """
        return item.name'''

    def format_result(self, item):
        """
        a more verbose display, used in the search results display.
        may contain html and multi-lines
        """
        return u"<span class='%s'>%s</span>" % (item.type, item.name)

    def get_item_label(self, item):
        return self.format_result(item)

    def get_item_id(self, item):
        return item.pk

    def get_item_value(self, item):
        return item.name

    def get_objects(self, ids):
        """
        given a list of ids, return the objects ordered as you would like them
        on the admin page. this is for displaying the currently selected items
        (in the case of a ManyToMany field)
        """
        results = []
        for id in ids:
            type, pk = id.split('-')
            if type == 'project':
                results.append(timepiece.Project.objects.get(pk=pk))
            elif type == 'business':
                results.append(timepiece.Business.objects.get(pk=pk))
            elif type == 'individual':
                results.append(auth_models.User.objects.get(pk=pk))
        return results
registry.register(QuickLookup)
