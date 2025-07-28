import logging
import sys
from logging.config import dictConfig
from pathlib import Path

from scrapy.settings import Settings
from scrapy.utils.log import DEFAULT_LOGGING, TopLevelFormatter
from scrapy.utils.python import to_bytes
from twisted.python import log
from twisted.python.log import startLoggingWithObserver
from twisted.python.logfile import DailyLogFile

from .conf import app_settings

DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
SILENT = CRITICAL + 1


def msg(message=None, **kwargs):
    kwargs["logLevel"] = kwargs.pop("level", INFO)
    kwargs.setdefault("system", "scrapyrt")
    log.msg(message, **kwargs)


def err(_stuff=None, _why=None, **kwargs):
    kwargs["logLevel"] = kwargs.pop("level", ERROR)
    kwargs.setdefault("system", "scrapyrt")
    log.err(_stuff, _why, **kwargs)


class ScrapyrtFileLogObserver(log.FileLogObserver):
    def __init__(self, f, encoding="utf-8"):
        self.encoding = encoding.lower()
        log.FileLogObserver.__init__(self, f)

    def _adapt_eventdict(self, event_dict):
        """Adapt event dict making it suitable for logging with Scrapyrt log
        observer.

        :return: adapted event_dict, None if message should be ignored.

        """
        if event_dict.get("system") == "scrapy":
            return None
        if "HTTPChannel" in event_dict.get(
            "system",
        ) and "Log opened." in event_dict.get("message", ""):
            # useless log message caused by scrapy.log.start
            return None
        return event_dict

    def _unicode_to_str(self, event_dict):
        message = event_dict.get("message")
        if message:
            event_dict["message"] = tuple(to_bytes(x, self.encoding) for x in message)
        return event_dict

    def emit(self, eventDict):
        eventDict = self._adapt_eventdict(eventDict)
        if eventDict is None:
            return
        eventDict = self._unicode_to_str(eventDict)
        log.FileLogObserver.emit(self, eventDict)


class SpiderFilter(logging.Filter):  # pylint: disable=too-few-public-methods
    """Filter messages from other spiders and undefined loggers.

    Accept messages that have 'spider' key in extra and it matches given spider.

    """

    def __init__(self, spider):
        super().__init__()
        self.spider = spider

    def filter(self, record):
        spider = getattr(record, "spider", None)
        return spider and spider is self.spider


def setup_logging():
    if app_settings.LOG_FILE:
        log_dir = Path(app_settings.LOG_DIR)
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
        logfile = DailyLogFile.fromFullPath(log_dir / app_settings.LOG_FILE)
    else:
        logfile = sys.stderr
    file_observer = ScrapyrtFileLogObserver(logfile, app_settings.LOG_ENCODING)
    startLoggingWithObserver(file_observer.emit, setStdout=False)

    # setup general logging for Scrapy
    if not sys.warnoptions:
        # Route warnings through python logging
        logging.captureWarnings(True)

    python_observer = log.PythonLoggingObserver("twisted")
    python_observer.start()
    logging.root.setLevel(logging.NOTSET)
    dictConfig(DEFAULT_LOGGING)


def setup_spider_logging(spider, settings):
    """Initialize and configure default loggers.

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
    filename = settings.get("LOG_FILE")
    handler: logging.Handler
    if filename:
        encoding = settings.get("LOG_ENCODING")
        handler = logging.FileHandler(filename, encoding=encoding)
    elif settings.getbool("LOG_ENABLED"):
        handler = logging.StreamHandler()
    else:
        handler = logging.NullHandler()
    formatter = logging.Formatter(
        fmt=settings.get("LOG_FORMAT"),
        datefmt=settings.get("LOG_DATEFORMAT"),
    )
    handler.setFormatter(formatter)
    handler.setLevel(settings.get("LOG_LEVEL"))
    filters = [
        TopLevelFormatter(["scrapy"]),
        SpiderFilter(spider),
    ]
    for _filter in filters:
        handler.addFilter(_filter)
    logging.root.addHandler(handler)

    _cleanup_functions = [
        lambda: [handler.removeFilter(f) for f in filters],  # type: ignore[func-returns-value]
        lambda: logging.root.removeHandler(handler),
        handler.close,
    ]

    def cleanup():
        for func in _cleanup_functions:
            func()

    return cleanup
