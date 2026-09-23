import datetime
import unittest
from unittest import mock

from django.utils import translation

from ajax_datatable.utils import date_format_to_strptime
from ajax_datatable.utils import format_datetime
from ajax_datatable.utils import parse_date


class DateFormatToStrptimeTestCase(unittest.TestCase):

    def test_numeric_formats_are_converted(self):
        self.assertEqual(date_format_to_strptime('m/d/Y'), '%m/%d/%Y')
        self.assertEqual(date_format_to_strptime('d.m.Y'), '%d.%m.%Y')
        # 'j' and 'n' drop the leading zero when rendering, but strptime
        # accepts both padded and unpadded values
        self.assertEqual(date_format_to_strptime('j-n-Y'), '%d-%m-%Y')
        # anything which is not a specifier stays literal, CJK included
        self.assertEqual(date_format_to_strptime('Y年n月j日'), '%Y年%m月%d日')

    def test_month_names_cannot_be_converted(self):
        # 'M' and 'F' render a translated month name: strptime matches month
        # names in the C locale only, so we decline the conversion
        self.assertIsNone(date_format_to_strptime('d M Y'))
        self.assertIsNone(date_format_to_strptime('j F Y'))

    def test_escaped_formats_are_declined(self):
        self.assertIsNone(date_format_to_strptime(r'd \d\i m'))


class DateRoundTripTestCase(unittest.TestCase):
    """
    Whatever format_datetime() renders, parse_date() must read back: the user
    filters a date column by copying what the table shows him.
    """

    # every language we ship a SHORT_DATE_FORMAT conversion for
    LANGUAGES = ['en', 'it', 'fr', 'es', 'de', 'pt', 'ja', 'pl', 'nl', 'zh-hans']

    DATE = datetime.date(2026, 3, 7)

    def assertRoundTrip(self, language):
        with translation.override(language):
            rendered = format_datetime(self.DATE, include_time=False)
            self.assertEqual(parse_date(rendered), self.DATE, rendered)

    def test_round_trip_localized(self):
        with mock.patch('ajax_datatable.utils.USE_L10N', True):
            for language in self.LANGUAGES:
                with self.subTest(language=language):
                    self.assertRoundTrip(language)

    def test_round_trip_not_localized(self):
        with mock.patch('ajax_datatable.utils.USE_L10N', False):
            for language in self.LANGUAGES + ['tr']:
                with self.subTest(language=language):
                    # with localization off every language renders the very
                    # same neutral format, and reads it back
                    with translation.override(language):
                        self.assertEqual(
                            format_datetime(self.DATE, include_time=False),
                            '03/07/2026'
                        )
                    self.assertRoundTrip(language)

    def test_month_name_languages_fall_back_to_input_formats(self):
        # 'tr' renders "07 Mar 2026", which we cannot read back; filtering
        # keeps working with the input formats the locale declares
        with mock.patch('ajax_datatable.utils.USE_L10N', True):
            with translation.override('tr'):
                self.assertEqual(
                    format_datetime(self.DATE, include_time=False),
                    '07 Mar 2026'
                )
                self.assertEqual(parse_date('07/03/2026'), self.DATE)
                with self.assertRaises(ValueError):
                    parse_date('07 Mar 2026')
