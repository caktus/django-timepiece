from timepiece.templatetags import timepiece_tags as tags
from timepiece.tests.base import TimepieceDataTestCase


class HumanizeSecondsTestCase(TimepieceDataTestCase):

    def test_default_format(self):
        seconds_display = tags.humanize_seconds((5.5 * 3600) + 3)
        self.assertEqual(seconds_display, '05:30:03',
            "Given (5.5 * 3600) + 3 seconds, should return 5h30m3s in %H:%M:%S"
        )

    def test_format_specified(self):
        seconds_display = tags.humanize_seconds(5.75 * 3600, '%H:%M')
        self.assertEqual(seconds_display, '05:45',
            "Given '%H:%M' as second argument, should return in that format"
        )
        seconds_display = tags.humanize_seconds(5.75 * 3600, '%H:%M:%S')
        self.assertEqual(seconds_display, '05:45:00',
            "Given '%H:%M:%S' as second argument, should return in that format"
        )

    def test_negative_seconds(self):
        seconds_display = tags.humanize_seconds((-2.5 * 3600) - 4)
        self.assertEqual(seconds_display, '-02:30:04',
            "Given negative seconds, should return as -%H:%M:%S"
        )


class HumanizeHoursTestCase(TimepieceDataTestCase):

    def test_default_format(self):
        hours_display = tags.humanize_hours('3.25')
        self.assertEqual(hours_display, '03:15',
            "Given 3.25 hours, should return 3h15m in %H:%M"
        )

    def test_format_specified(self):
        hours_display = tags.humanize_hours('1.75', '%H:%M')
        self.assertEqual(hours_display, '01:45',
            "Given '%H:%M' as second argument, should return in that format"
        )
        hours_display = tags.humanize_hours('1.76', '%H:%M:%S')
        self.assertEqual(hours_display, '01:45:36',
            "Given '%H:%M:%S' as second argument, should return in that format"
        )
