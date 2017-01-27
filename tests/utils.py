# -*- coding: utf-8 -*-
import os
import socket

from scrapy.settings import Settings

from . import TESTS_PATH

LOCALHOST = 'localhost'


def get_testenv():
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.realpath(os.path.join(TESTS_PATH, '..'))
    return env


def get_settings():
    """Settings with all extensions disabled."""
    return Settings({
        'EXTENSIONS': {
            'scrapy.extensions.throttle.AutoThrottle': None,
            'scrapy.extensions.feedexport.FeedExporter': None,
            'scrapy.extensions.logstats.LogStats': None,
            'scrapy.extensions.closespider.CloseSpider': None,
            'scrapy.extensions.corestats.CoreStats': None,
            'scrapy.extensions.memusage.MemoryUsage': None,
            'scrapy.extensions.memdebug.MemoryDebugger': None,
            'scrapy.extensions.spiderstate.SpiderState': None,
            'scrapy.extensions.telnet.TelnetConsole': None,
        }
    })
