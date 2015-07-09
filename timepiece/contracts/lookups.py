from django.utils.safestring import mark_safe

from selectable.base import ModelLookup
from selectable.registry import registry

from timepiece.contracts.models import ProjectContract


class ContractLookup(ModelLookup):
    model = ProjectContract
    search_fields = ('name__icontains',)

    def get_item_label(self, contract):
        return mark_safe(u'<span class="project">%s</span>' %
                self.get_item_value(contract))

    def get_item_value(self, contract):
        # return str(project) if project else ''
        return '%s' % (contract.name) if contract else ''

registry.register(ContractLookup)
