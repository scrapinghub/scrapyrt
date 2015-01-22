# -*- coding: utf-8 -*-
from functools import wraps
import warnings

from .exceptions import ScrapyrtDeprecationWarning


def deprecated(use_instead=None):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.

    Taken from Scrapy.
    """

    def deco(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            message = "Call to deprecated function %s." % func.__name__
            if use_instead:
                message += " Use %s instead." % use_instead
            warnings.warn(message, category=ScrapyrtDeprecationWarning,
                          stacklevel=2)
            return func(*args, **kwargs)

        return wrapped

    if callable(use_instead):
        deco = deco(use_instead)
        use_instead = None
    return deco
