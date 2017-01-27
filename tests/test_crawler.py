# -*- coding: utf-8 -*-
from scrapy.utils.engine import get_engine_status
from twisted.internet import defer
from twisted.trial import unittest

from scrapyrt.core import ScrapyrtCrawler

from .servers import MockServer
from .spiders import SingleRequestSpider
from .utils import get_settings


class TestCrawler(unittest.TestCase):
    """Spider shouldn't make start requests if list of start_requests
    wasn't passed to 'crawl' method.

    """

    def setUp(self):
        self.site = MockServer()
        self.site.start()
        self.settings = get_settings()
        self.settings['EXTENSIONS']['scrapy.extensions.corestats.CoreStats'] = 0
        self.engine_status = []

    def tearDown(self):
        self.site.stop()

    def cb(self, response):
        self.engine_status.append(get_engine_status(self.crawler.engine))

    def _assert_no_requests(self):
        self.assertEqual(len(self.engine_status), 0, self.engine_status)
        stats = self.crawler.stats.get_stats()
        self.assertNotIn('scheduler/enqueued', stats)
        self.assertNotIn('scheduler/dequeued', stats)
        self.assertNotIn('downloader/request_count', stats)
        self.assertNotIn('downloader/response_count', stats)

    def _assert_engine_worked(self):
        stats = self.crawler.stats.get_stats()
        self.assertIn('start_time', stats)
        self.assertIn('finish_time', stats)
        self.assertEquals(stats['finish_reason'], 'finished')

    @defer.inlineCallbacks
    def test_crawl_start_requests_disabled(self):
        self.crawler = ScrapyrtCrawler(
            SingleRequestSpider, self.settings, start_requests=False)
        yield self.crawler.crawl(seed=self.site.url(), callback_func=self.cb)
        self._assert_engine_worked()
        self._assert_no_requests()

    @defer.inlineCallbacks
    def test_crawl_start_requests_enabled(self):
        self.crawler = ScrapyrtCrawler(
            SingleRequestSpider, self.settings, start_requests=True)
        yield self.crawler.crawl(seed=self.site.url(), callback_func=self.cb)
        self._assert_engine_worked()
        self.assertEqual(len(self.engine_status), 1, self.engine_status)
        est = dict(self.engine_status[0])
        self.assertEqual(est['engine.spider.name'], self.crawler.spider.name)
        self.assertEqual(est['len(engine.scraper.slot.active)'], 1)
        stats = self.crawler.stats.get_stats()
        self.assertEqual(stats['scheduler/enqueued'], 1)
        self.assertEqual(stats['scheduler/dequeued'], 1)
        self.assertEqual(stats['downloader/request_count'], 1)
        self.assertEqual(stats['downloader/response_count'], 1)

    @defer.inlineCallbacks
    def test_crawl_start_requests_default(self):
        self.crawler = ScrapyrtCrawler(SingleRequestSpider, self.settings)
        yield self.crawler.crawl(seed=self.site.url(), callback_func=self.cb)
        self._assert_engine_worked()
        self._assert_no_requests()

