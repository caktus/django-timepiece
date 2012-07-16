Settings
=====================

.. _EXTRA_NAV:

EXTRA_NAV
--------------------------------

This is an optional settings that is used to add extra navigation items to the 
global navigation bar displayed at the top of each django-timepiece page. The 
setting uses `Twitter Bootstrap's <http://twitter.github.com/bootstrap/>`_ 
dropdown navigation. The setting can be declared as follows:

    .. code-block:: python

        EXTRA_NAV = {
            'Dropdown Text': [
                ('named_url_1', 'Dropdown Item #1',),
                ('named_url_2', 'Dropdown Item #2',),
            ], ...
        }

For example, the following would add a "Paste Bin" dropdown menu with the two 
links "Make a Paste" and "View my Pastes" as menu items in that dropdown.

    .. code-block:: python

        EXTRA_NAV = {
            'Paste Bin': [
                ('create_paste_view', 'Make a Paste',),
                ('user_paste_view', 'View my Pastes',),
            ],
        }

You can add as many menu items as you wish and are only limited by the space 
available in the navigation bar. Any navigation item that you add will appear 
following the django-timepiece related navigation items.

Note: You must have the context processor `timepiece.context_processors.extra_nav` 
listed in Django's `TEMPLATE_CONTEXT_PROCESSORS` setting.