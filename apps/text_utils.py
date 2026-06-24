import re


def first_upper(value):
    value = _clean(value)
    if not value:
        return ''
    return value[0].upper() + value[1:]


def first_upper_or_none(value):
    value = first_upper(value)
    return value or None


def upper_code(value):
    value = _clean(value)
    return value.upper()


def _clean(value):
    return re.sub(r'\s+', ' ', (value or '').strip())
