import logging
from contextlib import contextmanager
from copy import copy
from pathlib import Path

import pytest
from scrapy.settings.default_settings import LOG_DATEFORMAT, LOG_FORMAT, LOG_LEVEL

from scrapyrt.log import setup_spider_logging


@contextmanager
def preserve_root_handlers():
    original_handlers = copy(logging.root.handlers)
    try:
        yield
    finally:
        logging.root.handlers = original_handlers


@pytest.mark.parametrize(
    ("settings", "expected"),
    (
        (
            {},
            {
                "cls": logging.StreamHandler,
                "fmt": LOG_FORMAT,
                "datefmt": LOG_DATEFORMAT,
                "level": LOG_LEVEL,
            },
        ),
        (
            {
                "LOG_ENABLED": False,
                "LOG_FORMAT": "[%(name)s @ %(asctime)s] %(levelname)s: %(message)s",
                "LOG_DATEFORMAT": "%Y-%m-%d %H:%M:%S.0000",
                "LOG_LEVEL": "ERROR",
            },
            {
                "cls": logging.NullHandler,
                "fmt": "[%(name)s @ %(asctime)s] %(levelname)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S.0000",
                "level": "ERROR",
            },
        ),
    ),
)
def test_setup_spider_logging(settings, expected):
    spider = None

    with preserve_root_handlers():
        setup_spider_logging(spider, settings)
        handler = logging.root.handlers[-1]

    assert handler.__class__ is expected["cls"]
    assert handler.formatter is not None
    assert handler.formatter._fmt == expected["fmt"]
    assert handler.formatter.datefmt == expected["datefmt"]
    assert logging.getLevelName(handler.level) == expected["level"]


def test_setup_spider_logging_file():
    spider = None
    log_file = "foo.log"
    settings = {"LOG_FILE": log_file}

    with preserve_root_handlers():
        setup_spider_logging(spider, settings)
        handler = logging.root.handlers[-1]

    assert isinstance(handler, logging.FileHandler)
    assert handler.baseFilename == str(Path(log_file).absolute())
    assert handler.encoding == "utf-8"
    assert handler.formatter is not None
    assert handler.formatter._fmt == LOG_FORMAT
    assert handler.formatter.datefmt == LOG_DATEFORMAT
    assert logging.getLevelName(handler.level) == LOG_LEVEL
    handler.close()
