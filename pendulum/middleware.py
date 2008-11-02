from django.contrib.auth.views import login
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

class PendulumMiddleware:
    """
    This middleware ensures that anyone trying to access Pendulum must be logged in
    """
    def process_request(self, request):
        entry_url = reverse('pendulum-entries')

        if request.path[:len(entry_url)] == entry_url and request.user.is_anonymous():
            if request.POST:
                return login(request)
            else:
                return HttpResponseRedirect('/accounts/login/?next=%s' % request.path)