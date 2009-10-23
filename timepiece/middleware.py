from django.contrib.auth.views import login
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.conf import settings
from timepiece.models import PendulumConfiguration

SITE = Site.objects.get_current()
admin_url = reverse('admin_timepiece_timepiececonfiguration_add')
login_url = getattr(settings, 'LOGIN_URL', '/accounts/login/')

class PendulumMiddleware:
    """
    This middleware ensures that anyone trying to access Pendulum must be
    logged in.  If Pendulum hasn't been configured for the current site, the
    staff users will be redirected to the page to configure it.
    """
    def process_request(self, request):
        try:
            SITE.timepiececonfiguration
        except PendulumConfiguration.DoesNotExist:
            # this will force the user to configure timepiece if they're staff
            if request.user.has_perm('add_timepiececonfiguration') and \
                request.path not in (admin_url, login_url):
                # leave the user a message
                request.user.message_set.create(message='Please configure Pendulum for %s' % SITE)

                return HttpResponseRedirect(admin_url)
        else:
            entry_url = reverse('timepiece-entries')

            if request.path[:len(entry_url)] == entry_url and request.user.is_anonymous():
                if request.POST:
                    return login(request)
                else:
                    return HttpResponseRedirect('%s?next=%s' % (login_url, request.path))