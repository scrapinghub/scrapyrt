# -*- coding: utf-8 -*-
import logging
import os
import sys
from logging.config import dictConfig

from scrapy.settings import Settings
from scrapy.utils.log import DEFAULT_LOGGING, TopLevelFormatter
from twisted.python import log
from twisted.python.log import startLoggingWithObserver
from twisted.python.logfile import DailyLogFile

from .conf import settings as scrapyrt_settings
from .utils import to_bytes

DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
SILENT = CRITICAL + 1


def msg(message=None, **kwargs):
    kwargs['logLevel'] = kwargs.pop('level', INFO)
    kwargs.setdefault('system', 'scrapyrt')
    if message is None:
        log.msg(**kwargs)
    else:
        log.msg(message, **kwargs)


def err(_stuff=None, _why=None, **kwargs):
    kwargs['logLevel'] = kwargs.pop('level', ERROR)
    kwargs.setdefault('system', 'scrapyrt')
    log.err(_stuff, _why, **kwargs)


class ScrapyrtFileLogObserver(log.FileLogObserver):

    def __init__(self, f, encoding='utf-8'):
        self.encoding = encoding.lower()
        log.FileLogObserver.__init__(self, f)

    def _adapt_eventdict(self, event_dict):
        """Adapt event dict making it suitable for logging with Scrapyrt log
        observer.

        :return: adapted event_dict, None if message should be ignored.

        """
        if event_dict.get('category') == 'scrapy.exceptions.ScrapyDeprecationWarning':
            # ignore Scrapy deprecation warning in ScrapyRT log
            return
        if event_dict.get('system') == 'scrapy':
            return
        if ('HTTPChannel' in event_dict.get('system') and
                'Log opened.' in event_dict.get('message', '')):
            # useless log message caused by scrapy.log.start
            return
        return event_dict

    def _unicode_to_str(self, eventDict):
        message = eventDict.get('message')
        if message:
            eventDict['message'] = tuple(
                to_bytes(x, self.encoding) for x in message)
        return eventDict

    def emit(self, eventDict):
        eventDict = self._adapt_eventdict(eventDict)
        if eventDict is None:
            return
        eventDict = self._unicode_to_str(eventDict)
        log.FileLogObserver.emit(self, eventDict)


class SpiderFilter(logging.Filter):
    """Filter messages from other spiders and undefined loggers.

    Accept messages that have 'spider' key in extra and it matches given spider.

    """

    def __init__(self, spider):
        self.spider = spider

    def filter(self, record):
        spider = getattr(record, 'spider', None)
        return spider and spider is self.spider


def setup_logging():
    if not os.path.exists(scrapyrt_settings.LOG_DIR):
        os.makedirs(scrapyrt_settings.LOG_DIR)
    if scrapyrt_settings.LOG_FILE:
        logfile = DailyLogFile.fromFullPath(
            os.path.join(scrapyrt_settings.LOG_DIR,
                         scrapyrt_settings.LOG_FILE)
        )
    else:
        logfile = sys.stderr
    observer = ScrapyrtFileLogObserver(logfile, scrapyrt_settings.LOG_ENCODING)
    startLoggingWithObserver(observer.emit, setStdout=False)

    # setup general logging for Scrapy
    if not sys.warnoptions:
        # Route warnings through python logging
        logging.captureWarnings(True)

    observer = log.PythonLoggingObserver('twisted')
    observer.start()
    logging.root.setLevel(logging.NOTSET)
    dictConfig(DEFAULT_LOGGING)


def setup_spider_logging(spider, settings):
    """Initialize and configure default loggers

    Copied from Scrapy and updated, because version from Scrapy:

     1) doesn't close handlers and observers
     2) opens logobserver for twisted logging each time it's called -
        you can find N log observers logging the same message N
        after N crawls.

    so there's no way to reuse it.

    :return: method that should be called to cleanup handler.

    """
    if isinstance(settings, dict):
        settings = Settings(settings)

    # Looging stdout is a bad idea when mutiple crawls are running
    # if settings.getbool('LOG_STDOUT'):
    #     sys.stdout = StreamLogger(logging.getLogger('stdout'))
    filename = settings.get('LOG_FILE')
    if filename:
        encoding = settings.get('LOG_ENCODING')
        handler = logging.FileHandler(filename, encoding=encoding)
    elif settings.getbool('LOG_ENABLED'):
        handler = logging.StreamHandler()
    else:
        handler = logging.NullHandler()
    formatter = logging.Formatter(
        fmt=settings.get('LOG_FORMAT'),
        datefmt=settings.get('LOG_DATEFORMAT')
    )
    handler.setFormatter(formatter)
    handler.setLevel(settings.get('LOG_LEVEL'))
    filters = [
        TopLevelFormatter(['scrapy']),
        SpiderFilter(spider),
    ]
    for _filter in filters:
        handler.addFilter(_filter)
    logging.root.addHandler(handler)

    _cleanup_functions = [
        lambda: [handler.removeFilter(f) for f in filters],
        lambda: logging.root.removeHandler(handler),
        handler.close,
    ]

    def cleanup():
        for func in _cleanup_functions:
            try:
                func()
            except Exception as e:
                err(e)

    return cleanup
