from django.core.management.base import BaseCommand
from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--name',
                    default='Pendulum',
                    dest='name',
                    help='Specifies the name for the Pendulum user group.'),
        make_option('--reset',
                    default=False,
                    dest='reset',
                    help='Use this to revert the Pendulum user group to have all permission.'),
    )
    help = """Creates a default Pendulum user group with all permissions for entries,
including the ability to:

    - add entries
    - update entries
    - delete entries
    - clock in
    - clock out
    - pause/unpause entries"""
    args = '[--name="Pendulum Group"] [--reset=True]'

    def handle(self, **options):
        # grab some values from the parameter list
        reset = options.get('reset', False)
        name = options.get('name', 'Pendulum')

        self.validate(display_num_errors=False)

        # determine the content type for the Pendulum.Entry model
        from django.contrib.contenttypes.models import ContentType
        try:
            content_type = ContentType.objects.get(app_label='timepiece',
                                                   model='entry')
        except ContentType.DoesNotExist:
            print 'The content type for Pendulum.Entry is not available.  The user group cannot be created.'
            return

        # find all permissions for the Entry model
        from django.contrib.auth.models import Permission, Group
        permissions = Permission.objects.filter(content_type=content_type)

        if len(permissions) <= 3:
            print 'Please install the ContentTypes application.'
            return

        try:
            # remove the existing group if necessary
            if reset:
                Group.objects.filter(name=name).delete()

            # attempt to create a user group called "Pendulum" with all of the
            # available permissions for Entry objects
            group = Group.objects.create(name=name)
            group.permissions = permissions
            group.save()
        except Exception, e:
            print 'Failed to create default Pendulum user group.'
            print 'Do you already have a group called "%s"?' % name
        else:
            print 'Default user group "%s" created successfully.' % name
