from timepiece.templatetags import timepiece_tags as tags
from timepiece.tests.base import TimepieceDataTestCase


class HumanizeSecondsTestCase(TimepieceDataTestCase):

    def test_usual(self):
        seconds_display = tags.humanize_seconds((5.5 * 3600) + 3)
        self.assertEqual(seconds_display, u'05:30:03',
            "Should return u'05:30:03', returned {0}".format(seconds_display)
        )

    def test_negative_seconds(self):
        seconds_display = tags.humanize_seconds((-2.5 * 3600) - 4)
        self.assertEqual(seconds_display, u'-02:30:04',
            "Should return u'-02:30:04', returned {0}".format(seconds_display)
        )

    def test_overnight(self):
        seconds_display = tags.humanize_seconds((30 * 3600) + 2)
        self.assertEqual(seconds_display, u'30:00:02',
            "Should return u'30:00:02', returned {0}".format(seconds_display)
        )


class HumanizeHoursTestCase(TimepieceDataTestCase):

    def test_usual(self):
        hours_display = tags.humanize_hours('3.25')
        self.assertEqual(hours_display, u'03:15:00',
            "Given 3.25 hours, returned {0}, expected u'03:15:00'".format(
                hours_display)
        )

    def test_negative_seconds(self):
        hours_display = tags.humanize_hours('-2.75')
        self.assertEqual(hours_display, u'-02:45:00',
            "Given -2.75 hours, returned {0}, expected u'-02:45:00'".format(
                hours_display)
        )

    def test_overnight(self):
        hours_display = tags.humanize_hours('25.5')
        self.assertEqual(hours_display, u'25:30:00',
            "Given 25.5 hours, returned {0}, expected u'25:30:00'".format(
                hours_display)
        )
