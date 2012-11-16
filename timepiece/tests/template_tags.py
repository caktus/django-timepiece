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
        self.assertEqual(seconds_display, u'(02:30:04)',
            "Should return u'(02:30:04)', returned {0}".format(seconds_display)
        )

    def test_overnight(self):
        seconds_display = tags.humanize_seconds((30 * 3600) + 2)
        self.assertEqual(seconds_display, u'30:00:02',
            "Should return u'30:00:02', returned {0}".format(seconds_display)
        )

    def test_format(self):
        seconds_display = tags.humanize_seconds(120, '%M:%M:%M')
        expected = u'02:02:02'
        self.assertEqual(seconds_display, expected,
            "Should return {0}, return {1}".format(expected, seconds_display)
        )


class ConvertHoursToSecondsTestCase(TimepieceDataTestCase):

    def test_usual(self):
        seconds = tags.convert_hours_to_seconds('3.25')
        expected = int(3.25 * 3600)
        self.assertEqual(seconds, expected,
            "Given 3.25 hours, returned {0}, expected {1}".format(
                seconds, expected)
        )

    def test_negative_seconds(self):
        seconds = tags.convert_hours_to_seconds('-2.75')
        expected = int(-2.75 * 3600)
        self.assertEqual(seconds, expected,
            "Given -2.75 hours, returned {0}, expected {1}".format(
                seconds, expected)
        )
