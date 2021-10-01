from django.utils.decorators import method_decorator


def cbv_decorator(function_decorator):
    """Allows a function-based decorator to be used on a CBV."""

    def class_decorator(View):
        View.dispatch = method_decorator(function_decorator)(View.dispatch)
        return View
    return class_decorator


def format_totals(entry_dict, key="sum"):
    for entry in entry_dict:
        if entry[key]:
            entry[key] = "{0:.2f}".format(entry[key])


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
