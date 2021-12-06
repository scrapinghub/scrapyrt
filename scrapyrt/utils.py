import asyncio
import inspect
from contextlib import suppress

from scrapy import Request
from scrapy.utils.misc import load_object
from twisted.internet import asyncioreactor, error


def extract_scrapy_request_args(dictionary, raise_error=False):
    """
    :param dictionary: Dictionary with parameters passed to API
    :param raise_error: raise ValueError if key is not valid arg for
                        scrapy.http.Request
    :return: dictionary of valid scrapy.http.Request positional and keyword
            arguments.
    """
    result = dictionary.copy()
    args = inspect.getfullargspec(Request.__init__).args
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
        if not isinstance(text, str):
            raise TypeError('to_bytes must receive a unicode, str or bytes '
                            'object, got %s' % type(text).__name__)
        if encoding is None:
            encoding = 'utf-8'
        return text.encode(encoding, errors)


try:
    from scrapy.utils.reactor import install_reactor
except ImportError:
    def install_reactor(reactor_path, event_loop_path=None):
        """Installs the :mod:`~twisted.internet.reactor` with the specified
        import path. Also installs the asyncio event loop with the specified import
        path if the asyncio reactor is enabled"""
        reactor_class = load_object(reactor_path)
        if reactor_class is asyncioreactor.AsyncioSelectorReactor:
            with suppress(error.ReactorAlreadyInstalledError):
                if event_loop_path is not None:
                    event_loop_class = load_object(event_loop_path)
                    event_loop = event_loop_class()
                    asyncio.set_event_loop(event_loop)
                else:
                    event_loop = asyncio.get_event_loop()
                asyncioreactor.install(eventloop=event_loop)
        else:
            *module, _ = reactor_path.split(".")
            installer_path = module + ["install"]
            installer = load_object(".".join(installer_path))
            with suppress(error.ReactorAlreadyInstalledError):
                installer()

