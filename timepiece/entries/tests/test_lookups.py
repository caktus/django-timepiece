from django.test import TestCase
from django.test.client import RequestFactory

from timepiece.tests import factories
from timepiece.entries.lookups import ActivityLookup


class ActivityLookupTestCase(TestCase):
    """
    Tests that the ActivityLookup used by Selectable is looking up models
    the way we want it to.
    """

    def setUp(self):
        self.lookup = ActivityLookup()

    def test_get_query(self):
        """
        Tests whether we get the right results with a non-empty query.
        """
        activity1 = factories.Activity(name='foo')
        activity2 = factories.Activity(name='bar')
        activity3 = factories.Activity(name='baz')
        activity4 = factories.Activity(name='qux')

        activity_group = factories.ActivityGroup()
        activity_group.activities.add(activity1)
        activity_group.activities.add(activity2)
        activity_group.activities.add(activity3)
        activity_group.activities.add(activity4)

        project = factories.Project(activity_group=activity_group)

        request = RequestFactory().get('/selectable/entries-activitylookup', {
            'project': project.pk
        })

        data = self.lookup.get_query(request, 'a')

        self.assertNotIn(activity1, data)
        self.assertIn(activity2, data)
        self.assertIn(activity3, data)
        self.assertNotIn(activity4, data)

    def test_get_query_empty(self):
        """
        Tests whether a query with no associated project searches the entire
        set of activities, regardless of project.
        """
        activity1 = factories.Activity(name='foo')
        activity2 = factories.Activity(name='bar')
        activity3 = factories.Activity(name='baz')
        activity4 = factories.Activity(name='qux')

        activity_group1 = factories.ActivityGroup()
        activity_group1.activities.add(activity1)
        activity_group1.activities.add(activity2)

        activity_group2 = factories.ActivityGroup()
        activity_group2.activities.add(activity3)
        activity_group2.activities.add(activity4)

        request = RequestFactory().get('/selectable/entries-activitylookup', {
            'project': ''
        })

        data = self.lookup.get_query(request, '')

        self.assertIn(activity1, data)
        self.assertIn(activity2, data)
        self.assertIn(activity3, data)
        self.assertIn(activity4, data)

        data = self.lookup.get_query(request, 'a')

        self.assertNotIn(activity1, data)
        self.assertIn(activity2, data)
        self.assertIn(activity3, data)
        self.assertNotIn(activity4, data)
