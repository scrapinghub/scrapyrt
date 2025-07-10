from __future__ import annotations

import inspect

from scrapy import Request


def extract_scrapy_request_args(dictionary, raise_error=False):
    """Return a dictionary of valid scrapy.http.Request arguments.

    :param dictionary: Dictionary with parameters passed to API
    :param raise_error: raise ValueError if key is not valid arg for
                        scrapy.http.Request
    :return: dictionary of valid scrapy.http.Request positional and keyword
            arguments.
    """
    result = dictionary.copy()
    args = inspect.getfullargspec(Request.__init__).args
    for key in dictionary:
        if key not in args:
            result.pop(key)
            if raise_error:
                msg = "{!r} is not a valid argument for scrapy.Request.__init__"
                raise ValueError(msg.format(key))
    return result
