# -*- coding: utf-8 -*-
from scrapy.settings import Settings

from . import settings


def get_scrapyrt_settings(log_file=None):
    spider_settings = {
        "LOG_LEVEL": "DEBUG",
        "LOG_ENABLED": bool(log_file),
        "LOG_FILE": log_file,
        "LOG_STDOUT": False,
        "EXTENSIONS": {
            'scrapy.extensions.logstats.LogStats': None,
            'scrapy.webservice.WebService': None,
            'scrapy.extensions.telnet.TelnetConsole': None,
            'scrapy.extensions.throttle.AutoThrottle': None
        }
    }
    return spider_settings


def get_project_settings(module=None, custom_settings=None):
    crawler_settings = Settings()
    if module is None:
        module = settings.PROJECT_SETTINGS
    crawler_settings.setmodule(module, priority='project')
    if custom_settings:
        assert isinstance(custom_settings, dict)
        crawler_settings.setdict(custom_settings, priority='cmdline')
    return crawler_settings
