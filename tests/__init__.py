# -*- coding: utf-8 -*-
import os

from scrapy.utils.reactor import install_reactor

from scrapyrt.conf import app_settings

if app_settings.TWISTED_REACTOR is not None:
    install_reactor(app_settings.TWISTED_REACTOR)

TESTS_PATH = os.path.realpath(os.path.dirname(__file__))
PROJECT_PATH = os.path.realpath(os.path.join(TESTS_PATH, '..'))
SAMPLE_DATA = os.path.join(TESTS_PATH, 'sample_data')
