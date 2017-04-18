import inspect

import sys

import six
from scrapy import Request


def extract_scrapy_request_args(dictionary, raise_error=False):
    """
    :param dictionary: Dictionary with parameters passed to API
    :param raise_error: raise ValueError if key is not valid arg for
                        scrapy.http.Request
    :return: dictionary of valid scrapy.http.Request positional and keyword
            arguments.
    """
    result = dictionary.copy()
    args = inspect.getargspec(Request.__init__).args
    for key in dictionary.keys():
        if key not in args:
            result.pop(key)
            if raise_error:
                msg = u"{!r} is not a valid argument for scrapy.Request.__init__"
                raise ValueError(msg.format(key))
    return result


try:
    from scrapy.utils.python import to_bytes
except ImportError:
    def to_bytes(text, encoding=None, errors='strict'):
        """Return the binary representation of `text`. If `text`
        is already a bytes object, return it as-is."""
        if isinstance(text, bytes):
            return text
        if not isinstance(text, six.string_types):
            raise TypeError('to_bytes must receive a unicode, str or bytes '
                            'object, got %s' % type(text).__name__)
        if encoding is None:
            encoding = 'utf-8'
        return text.encode(encoding, errors)
