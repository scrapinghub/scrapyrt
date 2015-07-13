# -*- coding: utf-8 -*-
from mock import MagicMock
from scrapy import signals
from twisted.internet.defer import Deferred
from twisted.trial import unittest

from scrapyrt.core import CrawlManager, ScrapyrtCrawlerProcess

from .spiders import MetaSpider
from .utils import get_settings


class CralwerProcessTestCase(unittest.TestCase):

    def _mock_method(self, obj, method):
        msg = "can't mock, class {} doesn't have method {}".format(
            obj.__class__.__name__, method)
        assert hasattr(obj, method), msg
        setattr(obj, method, MagicMock(spec=lambda: None))

    def test_signals(self):
        """Need to be sure that all signals are bind to appropriate handlers
        right after crawler is created.

        """
        crawl_manager = CrawlManager('test', {'url': 'http://localhost'})

        signals_and_handlers = [
            ('item_scraped', 'get_item'),
            ('item_dropped', 'collect_dropped'),
            ('spider_idle', 'spider_idle'),
            ('spider_error', 'handle_spider_error'),
            ('request_scheduled', 'handle_scheduling'),
        ]
        for _, handler in signals_and_handlers:
            self._mock_method(crawl_manager, handler)
        settings = get_settings()
        crawler_process = ScrapyrtCrawlerProcess(settings, crawl_manager)
        dfd = crawler_process.crawl(MetaSpider)
        self.assertIsInstance(dfd, Deferred)
        crawler = crawl_manager.crawler
        for signal, handler in signals_and_handlers:
            crawler.signals.send_catch_log(
                signal=getattr(signals, signal), spider=crawler.spider)
            handler_mock = getattr(crawl_manager, handler)
            self.assertEquals(handler_mock.call_count, 1)
