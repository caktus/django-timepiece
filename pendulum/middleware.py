from django.contrib.auth.views import login
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.conf import settings
from pendulum.models import PendulumConfiguration

SITE = Site.objects.get_current()
admin_url = reverse('admin_pendulum_pendulumconfiguration_add')
login_url = getattr(settings, 'LOGIN_URL', '/accounts/login/')

class PendulumMiddleware:
    """
    This middleware ensures that anyone trying to access Pendulum must be
    logged in.  If Pendulum hasn't been configured for the current site, the
    staff users will be redirected to the page to configure it.
    """
    def process_request(self, request):
        try:
            SITE.pendulumconfiguration
        except PendulumConfiguration.DoesNotExist:
            # this will force the user to configure pendulum if they're staff
            if request.user.has_perm('add_pendulumconfiguration') and \
                request.path not in (admin_url, login_url):
                # leave the user a message
                request.user.message_set.create(message='Please configure Pendulum for %s' % SITE)

                return HttpResponseRedirect(admin_url)
        else:
            entry_url = reverse('pendulum-entries')

            if request.path[:len(entry_url)] == entry_url and request.user.is_anonymous():
                if request.POST:
                    return login(request)
                else:
                    return HttpResponseRedirect('%s?next=%s' % (login_url, request.path))