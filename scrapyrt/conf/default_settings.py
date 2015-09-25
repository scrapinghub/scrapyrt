# -*- coding: utf-8 -*-
"""Default scrapyrt settings."""

# Project settings module - found at server initialization
PROJECT_SETTINGS = None

# Path to server log file
LOG_FILE = None

# Path to spiders log directory
LOG_DIR = 'logs'

LOG_ENCODING = 'utf-8'

# Root server resource, should inherit from scrapyrt.resources.RealtimeAPI
SERVICE_ROOT = 'scrapyrt.resources.RealtimeApi'

# Resources list
RESOURCES = {
    'crawl.json': 'scrapyrt.resources.CrawlResource',
}

CRAWL_MANAGER = 'scrapyrt.core.CrawlManager'

# Limit spider run time
TIMEOUT_LIMIT = 1000
# disable in production
DEBUG = True
