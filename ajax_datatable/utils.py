import pprint
import datetime
from django.utils import timezone
from django.utils import formats
from .app_settings import USE_L10N

# Support for pytz is deprecated in Django 4.0 will be removed in Django 5.0
# import pytz

# Check if sqlparse is available for indentation
try:
    import sqlparse
except ImportError:
    class sqlparse:
        @staticmethod
        def format(text, *args, **kwargs):
            return text

# Check if termcolor is available for coloring
try:
    import termcolor
except ImportError:
    termcolor = None


# Check if Pygments is available for coloring
try:
    import pygments
    from pygments.lexers import SqlLexer
    from pygments.formatters import TerminalTrueColorFormatter
except ImportError:
    pygments = None


# def trace(message, prompt=''):
#     print('\n\x1b[1;36;40m', end='')
#     if prompt:
#         print(prompt + ':')
#     pprint.pprint(message)
#     print('\x1b[0m\n', end='')

# def prettyprint_queryset(qs):
#     print('\x1b[1;33;40m', end='')
#     # https://code.djangoproject.com/ticket/22973 !!!
#     try:
#         message = sqlparse.format(str(qs.query), reindent=True, keyword_case='upper')
#     except Exception as e:
#         message = str(e)
#         if not message:
#             message = repr(e)
#         message = 'ERROR: ' + message
#     print(message)
#     print('\x1b[0m\n')


def trace(message, color='cyan', on_color=None, attrs=None, prompt='', prettify=False):

    if prettify:
        text = pprint.pformat(message)
    else:
        text = str(message)

    if prompt:
        text = '=== ' + prompt + ': \n' + text

    if termcolor and (color or on_color):
        termcolor.cprint(text, color=color, on_color=on_color, attrs=attrs)
    else:
        print(text)


def prettyprint_query(query, colorize=True, prettify=True):

    def _str_query(sql):
        # Borrowed by morlandi from sant527
        # See: https://github.com/bradmontgomery/django-querycount/issues/22
        if prettify:
            sql = sqlparse.format(sql, reindent=True)
        if colorize and pygments:
            # Highlight the SQL query
            sql = pygments.highlight(
                sql,
                SqlLexer(),
                TerminalTrueColorFormatter(style='monokai')
                # TerminalTrueColorFormatter()
            )
        return sql

    sql = _str_query(query)
    print(sql)


def prettyprint_queryset(qs, colorize=True, prettify=True):
    prettyprint_query(str(qs.query), colorize=colorize, prettify=prettify)


# Django date format specifiers which have a strptime equivalent; anything
# else (a translated month name, for instance) cannot be read back.
DATE_FORMAT_SPECIFIERS = 'aAbcdDeEfFgGhHiIjlLmMnNoOPrsStTUuwWyYzZ'
STRPTIME_EQUIVALENTS = {
    'd': '%d', 'j': '%d',
    'm': '%m', 'n': '%m',
    'Y': '%Y', 'y': '%y',
}


def date_format_to_strptime(date_format):
    """
    Convert a Django date format ("d/m/Y") into the equivalent strptime
    pattern ("%d/%m/%Y"), so a date we rendered can be read back.

    Returns None when the format holds something strptime cannot match: 14 of
    the 83 locales shipped by Django render the month as a translated name,
    and those fall back to DATE_INPUT_FORMATS.
    """
    if '\\' in date_format:
        # escaped literals: don't attempt the conversion
        return None
    pattern = ''
    for ch in date_format:
        if ch in STRPTIME_EQUIVALENTS:
            pattern += STRPTIME_EQUIVALENTS[ch]
        elif ch in DATE_FORMAT_SPECIFIERS:
            return None
        elif ch == '%':
            pattern += '%%'
        else:
            pattern += ch
    return pattern


def format_datetime(dt, include_time=True):
    """
    Here we adopt the following rule:
    1) format date according to active localization
    2) append time in military format
    """
    if dt is None:
        return ''

    if isinstance(dt, datetime.datetime):
        try:
            dt = timezone.localtime(dt)
        except ValueError:
            dt = timezone.make_aware(dt)
        # Support for pytz is deprecated in Django 4.0 will be removed in Django 5.0
        # except Exception:
        #     local_tz = pytz.timezone(getattr(settings, 'TIME_ZONE', 'UTC'))
        #     dt = local_tz.localize(dt)

    else:
        assert isinstance(dt, datetime.date)
        include_time = False

    text = formats.date_format(dt, use_l10n=USE_L10N, format='SHORT_DATE_FORMAT')
    if include_time:
        text += dt.strftime(' %H:%M:%S')
    return text


def parse_date(formatted_date):
    """
    Read back a date rendered by format_datetime().

    The very format used for rendering is tried first, since that is what the
    user sees in the table and copies into the filter box; the input formats
    declared by the active locale follow.
    """
    date_formats = []
    rendering_format = date_format_to_strptime(
        formats.get_format('SHORT_DATE_FORMAT', use_l10n=USE_L10N))
    if rendering_format:
        date_formats.append(rendering_format)
    date_formats += formats.get_format('DATE_INPUT_FORMATS', use_l10n=USE_L10N)

    for date_format in date_formats:
        try:
            return datetime.datetime.strptime(formatted_date, date_format).date()
        except ValueError:
            continue
    raise ValueError
