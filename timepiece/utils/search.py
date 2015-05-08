from django import forms
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect
from django.views.generic import ListView
from django.views.generic.edit import FormMixin

from .views import GetDataFormMixin


class SearchForm(forms.Form):
    """Base form used for searching data."""
    search = forms.CharField(label='', required=False)

    def __init__(self, *args, **kwargs):
        super(SearchForm, self).__init__(*args, **kwargs)
        self.fields['search'].widget.attrs['placeholder'] = 'Search'


class SearchMixin(GetDataFormMixin, FormMixin):
    """Adds the ability to search and filter objects with ListView."""
    form_class = None
    redirect_if_one_result = False

    def filter_results(self, form, queryset):
        if form.is_valid():
            return self.filter_form_valid(form, queryset)
        elif not form.is_bound:
            return self.filter_form_unbound(form, queryset)
        else:
            return self.filter_form_invalid(form, queryset)

    def filter_form_invalid(self, form, queryset):
        """Return no results."""
        return queryset.none()

    def filter_form_valid(self, form, queryset):
        raise NotImplemented("Subclass must implement queryset filtering "
                             "when the search form is valid.")

    def filter_form_unbound(self, form, queryset):
        """Return all results."""
        return queryset.all()

    def get(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        self.form = self.get_form(form_class)
        self.object_list = self.get_queryset()
        self.object_list = self.filter_results(self.form, self.object_list)

        allow_empty = self.get_allow_empty()
        if not allow_empty and len(self.object_list) == 0:
            raise Http404("No results found.")

        context = self.get_context_data(form=self.form, object_list=self.object_list)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def render_to_response(self, context):
        """
        When the user makes a search and there is only one result, redirect
        to the result's detail page rather than rendering the list.
        """
        if self.redirect_if_one_result:
            if self.object_list.count() == 1 and self.form.is_bound:
                return redirect(self.object_list.get().get_absolute_url())
        return super(SearchMixin, self).render_to_response(context)


class SearchListView(SearchMixin, ListView):
    """Basic implementation which uses text search on specific fields."""
    form_class = SearchForm
    search_fields = []

    def filter_form_valid(self, form, queryset):
        search = form.cleaned_data['search']
        query = Q()
        for field in self.search_fields:
            query |= Q(**{field: search})
        return queryset.filter(query)
