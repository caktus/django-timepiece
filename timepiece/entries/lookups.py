from selectable.base import ModelLookup
from selectable.registry import registry

from timepiece.crm.models import Project
from timepiece.entries.models import Activity


class ActivityLookup(ModelLookup):
    model = Activity
    search_fields = ('name__icontains', )

    def get_query(self, request, term):
        results = super(ActivityLookup, self).get_query(request, term)
        project = Project.objects.get(pk=request.GET.get('project', ''))
        if project and project.activity_group:
            return project.activity_group.activities.all()
        return results

    def get_item_label(self, item):
        return u"%s" % (item.name)


registry.register(ActivityLookup)
