from selectable.base import ModelLookup
from selectable.registry import registry

from timepiece.crm.models import Project
from timepiece.entries.models import Activity


class ActivityLookup(ModelLookup):
    model = Activity
    search_fields = ('name__icontains', )

    def get_query(self, request, term):
        results = super(ActivityLookup, self).get_query(request, term)
        project_pk = request.GET.get('project', None)
        if project_pk not in [None, '']:
            project = Project.objects.get(pk=project_pk)
            if project and project.activity_group:
                return project.activity_group.activities.all().filter(name__icontains=term)
        return results

    def get_item_label(self, item):
        return u"%s" % (item.name)


registry.register(ActivityLookup)
