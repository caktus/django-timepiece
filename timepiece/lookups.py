from django.db.models import Q
from django.core.urlresolvers import reverse
from django.contrib.auth import models as auth_models

from timepiece import models as timepiece


class UserLookup(object):

    def get_query(self,q,request):
        """ return a query set.  you also have access to request.user if needed """
        return auth_models.User.objects.filter(
            Q(first_name__icontains=q) | 
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        ).select_related().order_by('last_name')[:10]
        
    def format_item(self,contact):
        """ simple display of an object when it is displayed in the list of selected objects """
        return unicode(contact)

    def format_result(self,contact):
        """ a more verbose display, used in the search results display.  may contain html and multi-lines """
        return u"<span class='individual'>%s %s</span>" % (contact.first_name, contact.last_name)

    def get_objects(self,ids):
        """ given a list of ids, return the objects ordered as you would like them on the admin page.
            this is for displaying the currently selected items (in the case of a ManyToMany field)
        """
        return auth_models.User.objects.filter(pk__in=ids)
