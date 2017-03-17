# -*- coding: utf-8 -*-
import os

import shutil
from scrapy.settings import Settings

from . import TESTS_PATH, SAMPLE_DATA

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


def generate_project(directory, site=None):
    source = os.path.join(SAMPLE_DATA, 'testproject')
    shutil.copytree(
        source, directory, ignore=shutil.ignore_patterns('*.pyc'))
    # Pass site url to spider doing start requests
    spider_name = "testspider_startrequests.py"
    spider_filename = os.path.join(directory, "testproject", "spider_templates", spider_name)
    spider_target_place = os.path.join(directory, "testproject", "spiders", spider_name)
    if not site:
        return
    with open(spider_filename) as spider_file:
        spider_string = spider_file.read().format(site.url("page1.html"), site.url("page2.html"))
        with open(spider_target_place, "wb") as file_target:
            file_target.write(spider_string.encode('utf8'))
