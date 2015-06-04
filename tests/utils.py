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
            'scrapy.contrib.throttle.AutoThrottle': None,
            'scrapy.contrib.feedexport.FeedExporter': None,
            'scrapy.contrib.logstats.LogStats': None,
            'scrapy.contrib.closespider.CloseSpider': None,
            'scrapy.contrib.corestats.CoreStats': None,
            'scrapy.contrib.memusage.MemoryUsage': None,
            'scrapy.contrib.memdebug.MemoryDebugger': None,
            'scrapy.contrib.spiderstate.SpiderState': None,
            'scrapy.telnet.TelnetConsole': None,
        }
    })
