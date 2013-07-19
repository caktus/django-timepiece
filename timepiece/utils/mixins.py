from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from timepiece import utils


class PermissionsRequiredMixin(object):
    # Required.
    permissions = None

    # Optional.
    raise_exception = False
    login_url = utils.get_setting('LOGIN_URL')
    redirect_field_name = REDIRECT_FIELD_NAME

    def dispatch(self, request, *args, **kwargs):
        if getattr(self, 'permissions', None) is None:
            raise ImproperlyConfigured('Class must define the permissions '
                    'attribute')

        if not request.user.has_perms(self.permissions):
            if self.raise_exception:
                raise PermissionDenied
            return redirect_to_login(request.get_full_path(),
                    self.login_url, self.redirect_field_name)

        return super(PermissionsRequiredMixin, self).dispatch(request, *args,
                **kwargs)


class LoginRequiredMixin(object):

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


class CommitOnSuccessMixin(object):

    @method_decorator(transaction.commit_on_success)
    def dispatch(self, *args, **kwargs):
        return super(CommitOnSuccessMixin, self).dispatch(*args, **kwargs)


class CsrfExemptMixin(object):

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(CsrfExemptMixin, self).dispatch(*args, **kwargs)
