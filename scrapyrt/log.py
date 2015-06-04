# -*- coding: utf-8 -*-
import logging
import os
import sys

from scrapy.utils.python import unicode_to_str
from twisted.python import log
from twisted.python.log import startLoggingWithObserver
from twisted.python.logfile import DailyLogFile

from .conf import settings

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
        if event_dict['system'] == 'scrapy':
            return
        if ('HTTPChannel' in event_dict['system'] and
                'Log opened.' in event_dict['message']):
            # useless log message caused by scrapy.log.start
            return
        return event_dict

    def _unicode_to_str(self, eventDict):
        message = eventDict.get('message')
        if message:
            eventDict['message'] = tuple(
                unicode_to_str(x, self.encoding) for x in message)
        return eventDict

    def emit(self, eventDict):
        eventDict = self._adapt_eventdict(eventDict)
        if eventDict is None:
            return
        eventDict = self._unicode_to_str(eventDict)
        log.FileLogObserver.emit(self, eventDict)


def setup_logging():
    if not os.path.exists(settings.LOG_DIR):
        os.makedirs(settings.LOG_DIR)
    if settings.LOG_FILE:
        logfile = DailyLogFile.fromFullPath(
            os.path.join(settings.LOG_DIR, settings.LOG_FILE)
        )
    else:
        logfile = sys.stderr
    observer = ScrapyrtFileLogObserver(logfile, settings.LOG_ENCODING)
    startLoggingWithObserver(observer.emit, setStdout=False)
