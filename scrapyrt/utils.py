import inspect
from scrapy import Request


def extract_scrapy_request_args(dictionary, raise_error=False):
    result = dictionary.copy()
    args = inspect.getargspec(Request.__init__).args
    for key in dictionary.keys():
        if key not in args:
            result.pop(key)
            if raise_error:
                msg = u"{!r} is not a valid argument for scrapy.Request.__init__"
                raise ValueError(msg.format(key))
    return result
