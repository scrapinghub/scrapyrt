# -*- coding: utf-8 -*-
import os
from time import sleep
import datetime

import pytest
from mock import patch, MagicMock
from scrapy import Item
from scrapy.exceptions import DontCloseSpider
from scrapy.http import Response
from scrapy.settings import Settings
from scrapy.utils.test import get_crawler
from twisted.internet.defer import Deferred
from twisted.python.failure import Failure
from twisted.trial import unittest
from twisted.web.error import Error

from scrapyrt.core import CrawlManager
from scrapyrt.conf import settings

from .spiders import MetaSpider


class TestCrawlManager(unittest.TestCase):

    def setUp(self):
        self.url = 'http://localhost'
        self.kwargs = {'url': self.url, 'dont_filter': True}
        self.crawler = MagicMock()
        self.spider = MetaSpider.from_crawler(self.crawler)
        self.crawler.spider = self.spider
        self.crawl_manager = self._create_crawl_manager()
        self.crawl_manager.crawler = self.crawler
        self.item = Item()
        self.response = Response('http://localhost')
        self.another_spider = MetaSpider.from_crawler(self.crawler)

    def _create_crawl_manager(self):
        crawl_manager = CrawlManager(self.spider.name, self.kwargs.copy())
        crawl_manager.crawler = self.crawler
        return crawl_manager


@patch('scrapyrt.core.ScrapyrtCrawlerProcess.crawl', return_value=Deferred())
class TestCrawl(TestCrawlManager):

    def test_crawl(self, crawler_process_mock):
        result = self.crawl_manager.crawl()
        self.assertIsInstance(result, Deferred)
        self.assertGreater(len(result.callbacks), 0)
        self.assertEqual(
            result.callbacks[0][0][0], self.crawl_manager.return_items)

    def test_no_spider(self, crawler_process_mock):
        # spider wasn't found
        crawler_process_mock.side_effect = KeyError
        exception = self.assertRaises(
            Error, self.crawl_manager.crawl)
        self.assertTrue(crawler_process_mock.called)
        self.assertEqual(exception.status, '404')

    def test_spider_exists(self, crawler_process_mock):
        result = self.crawl_manager.crawl()
        self.assertTrue(crawler_process_mock.called)
        self.assertIs(result, crawler_process_mock.return_value)

    def test_spider_arguments_are_passed(self, crawler_process_mock):
        spider_args = ['a', 'b']
        spider_kwargs = {'a': 1, 'b': 2}
        self.crawl_manager.crawl(*spider_args, **spider_kwargs)
        self.assertTrue(crawler_process_mock.called)
        call_args, call_kwargs = crawler_process_mock.call_args
        for arg in spider_args:
            self.assertIn(arg, call_args)
        self.assertDictContainsSubset(spider_kwargs, call_kwargs)


class TestGetProjectSettings(TestCrawlManager):

    def test_get_project_settings(self):
        result = self.crawl_manager.get_project_settings()
        self.assertIsInstance(result, Settings)


class TestSpiderIdle(TestCrawlManager):

    def setUp(self):
        super(TestSpiderIdle, self).setUp()
        self.crawler.spider = self.spider
        # test callback
        self.spider.parse_something = lambda: None
        self.crawl_manager.callback_name = 'parse_something'
        self.request = self.crawl_manager.request

    def _call_spider_idle(self):
        try:
            self.crawl_manager.spider_idle(self.spider)
        except DontCloseSpider:
            pass

    def test_spider_opened(self):
        self.assertIsNone(self.crawl_manager.request.callback)
        self._call_spider_idle()
        self.crawler.engine.crawl.assert_called_once_with(
            self.crawl_manager.request, self.spider)
        self.assertNotEqual(self.request, self.crawl_manager.request)
        self.assertEquals(
            self.crawl_manager.request.callback, self.spider.parse_something)

    def test_raise_error_if_not_callable(self):
        self.spider.parse_something = None
        self.assertRaises(
            AssertionError, self.crawl_manager.spider_idle, self.spider)
        self.assertFalse(self.crawler.engine.crawl.called)

    def test_modify_realtime_request(self):
        self.assertDictEqual(self.crawl_manager.request.meta, {})
        self.assertEqual(self.crawl_manager.request.method, 'GET')

        def modify_realtime_request(request):
            request = request.replace(method='POST')
            request.meta['foo'] = 'bar'
            return request

        self.spider.modify_realtime_request = modify_realtime_request
        self._call_spider_idle()
        self.crawler.engine.crawl.assert_called_once_with(
            self.crawl_manager.request, self.spider)
        self.assertEqual(self.crawl_manager.request.method, 'POST')
        self.assertEqual(self.crawl_manager.request.meta['foo'], 'bar')

    def test_modify_realtime_request_is_not_callable(self):
        self.spider.modify_realtime_request = None
        self._call_spider_idle()
        self.crawler.engine.crawl.assert_called_once_with(
            self.crawl_manager.request, self.spider)
        self.assertNotEqual(self.request, self.crawl_manager.request)


class TestHandleScheduling(TestCrawlManager):

    def setUp(self):
        super(TestHandleScheduling, self).setUp()
        self.crawl_manager.limit_requests = MagicMock()
        self.crawl_manager.limit_runtime = MagicMock()

    def test_handle_scheduling(self):
        self.crawl_manager.handle_scheduling(
            self.crawl_manager.request, self.spider)
        self.crawl_manager.limit_requests.assert_called_once_with(self.spider)
        self.crawl_manager.limit_runtime.assert_called_once_with(self.spider)

    def test_handle_scheduling_another_spider(self):
        self.crawl_manager.handle_scheduling(
            self.crawl_manager.request, self.another_spider)
        self.assertFalse(self.crawl_manager.limit_requests.called)
        self.assertFalse(self.crawl_manager.limit_runtime.called)


class TestLimitRuntime(TestCrawlManager):

    def setUp(self):
        super(TestLimitRuntime, self).setUp()
        self.crawl_manager.timeout_limit = 1
        self.crawler.stats.get_value.return_value = datetime.datetime.utcnow()

    def _test_limit_runtime(self):
        self.crawl_manager.limit_runtime(self.spider)
        self.assertFalse(self.crawler.engine.close_spider.called)
        sleep(1)
        self.crawl_manager.limit_runtime(self.spider)
        self.assertTrue(self.crawler.engine.close_spider.called)

    def test_limit_runtime(self):
        self._test_limit_runtime()

    def test_string_number_timeout_value(self):
        _timeout = settings.TIMEOUT_LIMIT
        try:
            settings.TIMEOUT_LIMIT = '1'
            self.crawl_manager = self._create_crawl_manager()
            self._test_limit_runtime()
        finally:
            settings.TIMEOUT_LIMIT = _timeout

    def test_wrong_timeout_value(self):
        _timeout = settings.TIMEOUT_LIMIT
        try:
            settings.TIMEOUT_LIMIT = 'foo'
            self.assertRaises(
                ValueError, CrawlManager, self.spider.name, self.kwargs.copy())
        finally:
            settings.TIMEOUT_LIMIT = _timeout


class TestHandleSpiderError(TestCrawlManager):

    def setUp(self):
        super(TestHandleSpiderError, self).setUp()
        self.exception_message = 'Foo'
        self.exception = Exception(self.exception_message)
        self.failure = Failure(self.exception)

    def test_handle_spider_error_debug_true(self):
        self.assertEqual(len(self.crawl_manager.errors), 0)
        self.crawl_manager.handle_spider_error(self.failure, self.spider)
        self.assertEqual(len(self.crawl_manager.errors), 1)
        self.assertIn('Traceback', self.crawl_manager.errors[0])
        self.assertIn(self.exception.__class__.__name__,
                      self.crawl_manager.errors[0])
        self.assertIn(self.exception_message, self.crawl_manager.errors[0])

    def test_handle_spider_error_debug_false(self):
        self.crawl_manager.debug = False
        self.assertEqual(len(self.crawl_manager.errors), 0)
        self.crawl_manager.handle_spider_error(self.failure, self.spider)
        self.assertEqual(len(self.crawl_manager.errors), 0)

    def test_handle_spider_error_another_spider(self):
        self.assertEqual(len(self.crawl_manager.errors), 0)
        self.crawl_manager.handle_spider_error(
            self.failure, self.another_spider)
        self.assertEqual(len(self.crawl_manager.errors), 0)


class TestLimitRequests(TestCrawlManager):

    def test_max_requests_not_set(self):
        for i in range(100):
            self.crawl_manager.limit_requests(self.spider)
        self.assertFalse(self.crawler.engine.close_spider.called)

    def test_max_requests_set(self):
        self.crawl_manager.max_requests = 10
        for i in range(self.crawl_manager.max_requests):
            self.crawl_manager.limit_requests(self.spider)
        self.assertFalse(self.crawler.engine.close_spider.called)
        self.crawl_manager.limit_requests(self.spider)
        self.assertTrue(self.crawler.engine.close_spider.called)


class TestGetItem(TestCrawlManager):

    def setUp(self):
        super(TestGetItem, self).setUp()
        self.item = Item()

    def test_get_item(self):
        self.assertEqual(len(self.crawl_manager.items), 0)
        self.crawl_manager.get_item(self.item, self.response, self.spider)
        self.assertEqual(len(self.crawl_manager.items), 1)
        self.assertEqual(self.crawl_manager.items[0], self.item)

    def test_get_item_another_spider(self):
        self.assertEqual(len(self.crawl_manager.items), 0)
        self.crawl_manager.get_item(
            self.item, self.response, self.another_spider)
        self.assertEqual(len(self.crawl_manager.items), 0)


class TestCollectDropped(TestCrawlManager):

    def setUp(self):
        super(TestCollectDropped, self).setUp()
        self.exception = Exception('foo')
        self.expected_result = {
            'item': self.item,
            'response': self.response,
            'exception': str(self.exception)
        }

    def test_collect_dropped(self):
        self.assertEqual(len(self.crawl_manager.items_dropped), 0)
        self.crawl_manager.collect_dropped(
            self.item, self.response, self.exception, self.spider)
        self.assertEqual(len(self.crawl_manager.items_dropped), 1)
        self.assertEqual(len(self.crawl_manager.items_dropped), 1)
        self.assertEqual(
            self.crawl_manager.items_dropped[0], self.expected_result)

    def test_collect_dropped_another_spider(self):
        self.assertEqual(len(self.crawl_manager.items_dropped), 0)
        self.crawl_manager.collect_dropped(
            self.item, self.response, self.exception, self.another_spider)
        self.assertEqual(len(self.crawl_manager.items_dropped), 0)


class TestReturnItems(TestCrawlManager):

    def setUp(self):
        super(TestReturnItems, self).setUp()
        self.stats = {
            'log_count/INFO': 6,
            'scheduler/enqueued/memory': 4,
            'scheduler/dequeued/memory': 4,
        }
        self.crawl_manager.crawler = MagicMock()
        self.crawl_manager.crawler.stats.get_stats.return_value = self.stats
        self.expected_result = {
            'items': self.crawl_manager.items,
            'items_dropped': self.crawl_manager.items_dropped,
            'stats': self.stats.copy(),
            'spider_name': self.spider.name,
        }

    def test_return_items(self):
        result = self.crawl_manager.return_items(None)
        self.assertDictContainsSubset(self.expected_result, result)
        self.assertEqual(list(sorted(self.stats.keys())), list(result['stats'].keys()))
        # debug = True by default
        self.assertIn('errors', result)
        self.assertEquals(result['errors'], self.crawl_manager.errors)

    def test_return_items_without_debug(self):
        self.crawl_manager.debug = False
        result = self.crawl_manager.return_items(None)
        self.assertDictEqual(self.expected_result, result)
        self.assertNotIn('errors', result)


class TestCreateSpiderRequest(TestCrawlManager):

    def test_valid_arguments(self):
        req = self.crawl_manager.create_spider_request(self.kwargs)
        self.assertTrue(req.dont_filter)
        self.assertEqual(req.url, self.url)

    def test_invalid_arguments(self):
        self.kwargs['url1'] = 'http://localhost/foo'
        exception = self.assertRaises(
            Error, self.crawl_manager.create_spider_request, self.kwargs)
        self.assertEqual(exception.status, '400')

    def test_invalid_url(self):
        self.kwargs['url'] = '//localhost/foo'
        exception = self.assertRaises(
            Error, self.crawl_manager.create_spider_request, self.kwargs)
        self.assertEqual(exception.status, '400')
        self.kwargs['url'] = 'localhost/foo'
        exception = self.assertRaises(
            Error, self.crawl_manager.create_spider_request, self.kwargs)
        self.assertEqual(exception.status, '400')


class TestStartRequests(unittest.TestCase):

    def setUp(self):
        self.url = 'http://localhost'
        self.kwargs = {'url': self.url}
        self.start_requests_mock = MagicMock()
        self.spidercls = MetaSpider
        self._start_requests = self.spidercls.start_requests
        self.spidercls.start_requests = self.start_requests_mock
        self.crawler = get_crawler(self.spidercls)

        class CustomCrawlManager(CrawlManager):

            def get_project_settings(self):
                crawl_settings = super(
                    CustomCrawlManager, self).get_project_settings()
                crawl_settings.setdict(
                    {'SPIDER_MODULES': 'tests.spiders'}, priority='cmdline')
                return crawl_settings

        self.crawl_manager = CustomCrawlManager(
            self.spidercls.name, self.kwargs.copy())
        self.crawl_manager.crawler = self.crawler

    def tearDown(self):
        self.spidercls.start_requests = self._start_requests

    @patch('scrapy.crawler.ExecutionEngine')
    def test_start_requests_true(self, _):
        self.crawl_manager.start_requests = True
        self.crawl_manager.crawl()
        self.assertEqual(self.start_requests_mock.call_count, 1)

    @patch('scrapy.crawler.ExecutionEngine')
    def test_start_requests_false(self, _):
        self.crawl_manager.start_requests = False
        self.crawl_manager.crawl()
        self.assertEqual(self.start_requests_mock.call_count, 0)


class TestCreateProperLogFile(TestCrawlManager):
    def test_filename(self):
        logdir = "some_dir_name"
        self.crawl_manager.log_dir = logdir
        path = self.crawl_manager._get_log_file_path()
        filename = os.path.basename(path)
        expected_format = '%Y-%m-%dT%H%M%S.%f.log'
        datetime_object = datetime.datetime.strptime(filename, expected_format)
        now = datetime.datetime.now()
        assert datetime_object
        delta = now - datetime_object
        assert delta.seconds < 60
