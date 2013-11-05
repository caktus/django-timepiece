from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.utils.decorators import method_decorator

from timepiece import utils


def cbv_decorator(function_decorator):
    """Allows a function-based decorator to be used on a CBV."""

    def class_decorator(View):
        View.dispatch = method_decorator(function_decorator)(View.dispatch)
        return View
    return class_decorator


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


class GetDataFormMixin(object):
    """Used with subclasses of FormMixin to use GET data from the request."""

    def get_form_data(self):
        return self.request.GET or None

    def get_form_kwargs(self):
        kwargs = super(GetDataFormMixin, self).get_form_kwargs()
        kwargs.update({
            'data': self.get_form_data(),
        })
        return kwargs
