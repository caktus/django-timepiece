import json

from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect
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


class RedirectMessageMixin(object):
    """Mix in messages to the user and allow custom redirects."""
    next_url_get_kwarg = 'next'
    success_url = reverse_lazy('dashboard')

    success_message = None
    success_message_type = messages.SUCCESS
    failure_message = None
    failure_message_type = messages.ERROR

    def add_failure_message(self):
        """Message to the user when the action cannot be completed."""
        if self.failure_message:
            msg = self.get_failure_message()
            messages.add_message(self.request, self.failure_message_type, msg)

    def add_success_message(self):
        """Message when the user has successfully completed an action."""
        if self.success_message:
            msg = self.get_success_message()
            messages.add_message(self.request, self.success_message_type, msg)

    def get_failure_message(self):
        return self.failure_message

    def get_success_message(self):
        return self.success_message.format(obj=self.object)

    def form_invalid(self, form):
        """Add a failure message before processing the invalid form."""
        self.add_failure_message()
        return super(RedirectMessageMixin, self).form_invalid(form)

    def get_success_url(self):
        """Add a success message and redirect the user.

        If a 'next' URL is specified in the request, redirect there rather
        than the default success URL.
        """
        self.add_success_message()

        next_url = None
        if self.next_url_get_kwarg:
            next_url = self.request.REQUEST.get(self.next_url_get_kwarg, None)
        if next_url:
            return next_url
        if hasattr(super(RedirectMessageMixin, self), 'get_success_url'):
            return super(RedirectMessageMixin, self).get_success_url()
        if getattr(self, 'success_url', None):
            return self.success_url
        raise ImproperlyConfigured("No URL to redirect to. Please provide a "
                "success_url.")


class AjaxableDeleteMixin(object):
    """Used with DeleteView to respond appropriately to AJAX POSTs."""

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if self.request.is_ajax():
            data = self.object.pk
            return HttpResponse(json.dumps(data),
                    content_type="application/json")
        return HttpResponseRedirect(self.get_success_url())
