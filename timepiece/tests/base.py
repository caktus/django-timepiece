from six.moves.urllib.parse import parse_qs, urlparse
from six.moves.urllib.parse import urlencode

from dateutil.relativedelta import relativedelta

from django.core.urlresolvers import reverse, reverse_lazy
from django.conf import settings
from django.contrib.auth import login
from django.http import HttpRequest
from django.utils import timezone
from django.utils.encoding import force_text

from . import factories


class ViewTestMixin(object):
    """Utilities for more easily testing views."""
    url_name = ''  # Must be defined by implementing class.

    # These may be defined as either attributes or properties on the
    # implementing class.
    url_kwargs = {}
    url_args = {}
    get_kwargs = {}
    post_data = {}

    login_url = reverse_lazy('auth_login')

    def _url(self, url_name=None, url_args=None, url_kwargs=None,
             get_kwargs=None):
        """Builds a URL with reverse(), then adds GET parameters."""
        url_name = url_name or self.url_name
        url_args = self.url_args if url_args is None else url_args
        url_kwargs = self.url_kwargs if url_kwargs is None else url_kwargs
        get_kwargs = self.get_kwargs if get_kwargs is None else get_kwargs

        url = reverse(url_name, args=url_args, kwargs=url_kwargs)
        if get_kwargs:
            url = '{0}?{1}'.format(url, urlencode(get_kwargs, doseq=True))
        return url

    def _get(self, url_name=None, url_args=None, url_kwargs=None,
             get_kwargs=None, url=None, *args, **kwargs):
        """Convenience wrapper for self.client.get.

        If url is not passed, it is built using url_name, url_args, url_kwargs.
        Get parameters may be added from get_kwargs.
        """
        url = url or self._url(url_name, url_args, url_kwargs, get_kwargs)
        return self.client.get(path=url, *args, **kwargs)

    def _post(self, data=None, url_name=None, url_args=None,
              url_kwargs=None, get_kwargs=None, url=None, *args, **kwargs):
        """Convenience wrapper for self.client.post.

        If url is not passed, it is built using url_name, url_args, url_kwargs.
        Get parameters may be added from get_kwargs.
        """
        url = url or self._url(url_name, url_args, url_kwargs, get_kwargs)
        data = self.post_data if data is None else data
        return self.client.post(path=url, data=data, *args, **kwargs)

    def _post_ajax(self, *args, **kwargs):
        """Convenience wrapper for making an AJAX post."""
        kwargs.setdefault('HTTP_X_REQUESTED_WITH', 'XMLHttpRequest')
        return self._post(*args, **kwargs)

    def _post_raw(self, *args, **kwargs):
        """
        By default, the Django test client interprets POST data as a
        dictionary. By using a different content type, it will take the data
        as is.
        """
        kwargs.setdefault('content_type', 'application/x-www-form-urlencoded')
        return self._post(*args, **kwargs)

    def assertRedirectsNoFollow(self, response, expected_url, use_params=True,
                                status_code=302):
        """Checks response redirect without loading the destination page.

        Django's assertRedirects method loads the destination page, which
        requires that the page be renderable in the current test context
        (possibly requiring additional, unrelated setup).
        """
        # Assert that the response has the correct redirect code.
        self.assertEqual(
            response.status_code, status_code,
            "Response didn't redirect as expected: Response code was {0} "
            "(expected {1})".format(response.status_code, status_code))

        # Assert that the response redirects to the correct base URL.
        # Use force_text to force evaluation of anything created by
        # reverse_lazy.
        response_url = force_text(response['location'])
        expected_url = force_text(expected_url)
        parsed1 = urlparse(response_url)
        parsed2 = urlparse(expected_url)
        self.assertEquals(
            parsed1.path, parsed2.path,
            "Response did not redirect to the expected URL: Redirect "
            "location was {0} (expected {1})".format(parsed1.path, parsed2.path))

        # Optionally assert that the response redirect URL has the correct
        # GET parameters.
        if use_params:
            self.assertDictEqual(
                parse_qs(parsed1.query), parse_qs(parsed2.query),
                "Response did not have the GET parameters expected: GET "
                "parameters were {0} (expected "
                "{1})".format(parsed1.query or {}, parsed2.query or {}))

    def assertRedirectsToLogin(self, response, login_url=None,
                               use_params=False, status_code=302):
        login_url = login_url or self.login_url
        return self.assertRedirectsNoFollow(
            response, login_url, use_params, status_code)

    def login_user(self, user):
        """Log in a user without need for a password.

        Adapted from
        http://jameswestby.net/weblog/tech/17-directly-logging-in-a-user-in-django-tests.html
        """
        # Log out the current user.
        self.client.logout()

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        engine = __import__(settings.SESSION_ENGINE, fromlist=['SessionStore'])

        # Create a fake request to store login details.
        request = HttpRequest()
        request.session = self.client.session or engine.SessionStore()
        login(request, user)

        # Set the cookie to represent the session.
        session_cookie = settings.SESSION_COOKIE_NAME
        self.client.cookies[session_cookie] = request.session.session_key
        self.client.cookies[session_cookie].update({
            'max-age': None,
            'path': '/',
            'domain': settings.SESSION_COOKIE_DOMAIN,
            'secure': settings.SESSION_COOKIE_SECURE or None,
            'expires': None,
        })

        # Save the session values.
        request.session.save()


class LogTimeMixin(object):

    def log_time(self, delta=None, billable=True, project=None, start=None,
                 end=None, status=None, pause=0, activity=None, user=None):
        if not user:
            user = self.user
        if delta and not end:
            hours, minutes = delta
        else:
            hours = 4
            minutes = 0
        if not start:
            start = timezone.now() - relativedelta(hour=0)
            # In case the default would fall off the end of the billing period
            if start.day >= 28:
                start -= relativedelta(days=1)
        if not end:
            end = start + relativedelta(hours=hours, minutes=minutes)
        data = {'user': user,
                'start_time': start,
                'end_time': end,
                'seconds_paused': pause,
                }
        if project:
            data['project'] = project
        else:
            data['project'] = factories.BillableProject()
        if activity:
            data['activity'] = activity
        else:
            if billable:
                data['activity'] = self.devl_activity
            else:
                data['activity'] = self.activity
        if status:
            data['status'] = status
        return factories.Entry(**data)
