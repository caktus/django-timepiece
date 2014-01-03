from collections import namedtuple


class Constants(object):
    """Wrapper for model constants to make code prettier and DRYer.

    For example::

        class Entry(models.Model):

            STATUSES = Constants(
                unverified=('0', 'Not Verified'),
                verified=('1', 'Verified')
                approved=('2', 'Approved'),
                invoiced=('3', 'Invoiced'),
                uninvoiced=('4', 'Not Invoiced'),
            )
            status = models.CharField(max_length=1, choices=STATUSES.choices(),
                                      default=STATUSES.unverified)

        >>> entry = Entry.objects.create()
        >>> entry.status
        '0'
        >>> entry.get_status_display()
        'Not Verified'
        >>> entry in Entry.objects.filter(status=Entry.STATUSES.unverified)
        True
    """
    Constant = namedtuple('Constant', ['codename', 'value', 'description'])

    def __init__(self, **kwargs):
        self._constants = []
        try:
            for codename, (value, description) in kwargs.items():
                if hasattr(self, codename):
                    msg = "'{0}' conflicts with an existing attribute."
                    raise Exception(msg.format(codename))
                else:
                    setattr(self, codename, value)
                self._constants.append(self.Constant(codename, value, description))
        except (ValueError, TypeError):
            msg = "Must pass in kwargs in format: **{'codename': (value, description)}"
            raise Exception(msg)

    def choices(self):
        """Django-style choices list to pass to a model or form field."""
        return [(c.value, c.description) for c in self._constants]

    def get_list(self, *codenames):
        """Returns a list of values corresponding with the codenames.

        For example::

            statuses = Entry.STATUSES.get_list('verified', 'approved')
            entries = Entry.objects.filter(status__in=statuses)
        """
        return [getattr(self, codename) for codename in codenames]
