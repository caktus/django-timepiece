from django.conf import settings

from timepiece.forms import QuickSearchForm


def timepiece_settings(request):
    default_famfamfam_url = settings.STATIC_URL + 'images/icons/'
    famfamfam_url = getattr(settings, 'FAMFAMFAM_URL', default_famfamfam_url)
    context = {
        'FAMFAMFAM_URL': famfamfam_url,
    }
    return context


def quick_search(request):
    return {
        'quick_search_form': QuickSearchForm(),
    }
