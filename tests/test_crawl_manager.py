import contextlib
import datetime as dt
import re
from pathlib import Path
from time import sleep
from unittest.mock import MagicMock

import pytest
from scrapy import Item
from scrapy.exceptions import DontCloseSpider
from scrapy.http import Response
from scrapy.settings import Settings
from twisted.python.failure import Failure
from twisted.trial import unittest
from twisted.web.error import Error

from scrapyrt.conf import app_settings
from scrapyrt.core import CrawlManager

from .spiders import MetaSpider


class TestCrawlManager(unittest.TestCase):
    def setUp(self):
        self.url = "http://localhost"
        self.kwargs = {"url": self.url, "dont_filter": True}
        self.crawler = MagicMock()
        self.spider = MetaSpider.from_crawler(self.crawler)
        self.crawler.spider = self.spider
        self.crawl_manager = self.create_crawl_manager()
        self.crawl_manager.crawler = self.crawler
        self.item = Item()
        self.response = Response("http://localhost")
        self.another_spider = MetaSpider.from_crawler(self.crawler)

    def create_crawl_manager(self, kwargs=None):
        kwargs = kwargs if kwargs else self.kwargs.copy()
        crawl_manager = CrawlManager(self.spider.name, kwargs)
        crawl_manager.crawler = self.crawler
        return crawl_manager


class TestGetProjectSettings(TestCrawlManager):
    def test_get_project_settings(self):
        result = self.crawl_manager.get_project_settings()
        assert isinstance(result, Settings)


class TestSpiderIdle(TestCrawlManager):
    def setUp(self):
        super().setUp()
        self.crawler.spider = self.spider
        # test callback
        self.spider.parse_something = lambda: None  # type: ignore[attr-defined]
        self.crawl_manager.callback_name = "parse_something"
        self.request = self.crawl_manager.request

    def _call_spider_idle(self):
        with contextlib.suppress(DontCloseSpider):
            self.crawl_manager.spider_idle(self.spider)

    def test_spider_opened(self):
        assert self.crawl_manager.request.callback is None
        self._call_spider_idle()
        self.crawler.engine.crawl.assert_called_once_with(self.crawl_manager.request)
        assert self.request != self.crawl_manager.request
        assert self.crawl_manager.request.callback == self.spider.parse_something  # type: ignore[attr-defined]

    def test_raise_error_if_not_callable(self):
        self.spider.parse_something = None  # type: ignore[attr-defined]
        self._call_spider_idle()
        assert self.crawl_manager.user_error is not None
        msg = b"Invalid spider callback parse_something"
        assert re.search(msg, self.crawl_manager.user_error.message)
        assert not self.crawler.engine.crawl.called

    def test_modify_realtime_request(self):
        assert self.crawl_manager.request.meta == {}
        assert self.crawl_manager.request.method == "GET"

        def modify_realtime_request(request):
            request = request.replace(method="POST")
            request.meta["foo"] = "bar"
            return request

        self.spider.modify_realtime_request = modify_realtime_request  # type: ignore[attr-defined]
        self._call_spider_idle()
        self.crawler.engine.crawl.assert_called_once_with(self.crawl_manager.request)
        assert self.crawl_manager.request.method == "POST"
        assert self.crawl_manager.request.meta["foo"] == "bar"

    def test_modify_realtime_request_is_not_callable(self):
        self.spider.modify_realtime_request = None  # type: ignore[attr-defined]
        self._call_spider_idle()
        self.crawler.engine.crawl.assert_called_once_with(self.crawl_manager.request)
        assert self.request != self.crawl_manager.request

    def test_pass_wrong_spider_errback(self):
        mng = self.create_crawl_manager(
            {"url": "http://localhost", "errback": "handle_error"},
        )

        with contextlib.suppress(DontCloseSpider):
            mng.spider_idle(self.spider)

        assert mng.request.errback is None

        assert mng.user_error is not None
        msg = b"Invalid spider errback"
        assert re.search(msg, mng.user_error.message)

    def test_pass_good_spider_errback(self):
        mng = self.create_crawl_manager(
            {"url": "http://localhost", "errback": "handle_error"},
        )
        self.crawler.spider.handle_error = lambda x: x
        with contextlib.suppress(DontCloseSpider):
            mng.spider_idle(self.spider)

        assert callable(mng.request.errback)
        assert mng.request.errback("something") == "something"


class TestHandleScheduling(TestCrawlManager):
    def setUp(self):
        super().setUp()
        self.crawl_manager.limit_requests = MagicMock()
        self.crawl_manager.limit_runtime = MagicMock()

    def test_handle_scheduling(self):
        self.crawl_manager.handle_scheduling(self.crawl_manager.request, self.spider)
        self.crawl_manager.limit_requests.assert_called_once_with(self.spider)
        self.crawl_manager.limit_runtime.assert_called_once_with(self.spider)

    def test_handle_scheduling_another_spider(self):
        self.crawl_manager.handle_scheduling(
            self.crawl_manager.request,
            self.another_spider,
        )
        assert not self.crawl_manager.limit_requests.called
        assert not self.crawl_manager.limit_runtime.called


class TestLimitRuntime(TestCrawlManager):
    def setUp(self):
        super().setUp()
        self.crawl_manager.timeout_limit = 1
        self.crawler.stats.get_value.return_value = dt.datetime.now(dt.timezone.utc)

    def _test_limit_runtime(self):
        self.crawl_manager.limit_runtime(self.spider)
        assert not self.crawler.engine.close_spider.called
        sleep(1)
        self.crawl_manager.limit_runtime(self.spider)
        assert self.crawler.engine.close_spider.called

    def test_limit_runtime(self):
        self._test_limit_runtime()

    def test_string_number_timeout_value(self):
        _timeout = app_settings.TIMEOUT_LIMIT
        try:
            app_settings.TIMEOUT_LIMIT = "1"  # type: ignore[assignment]
            self.crawl_manager = self.create_crawl_manager()
            self._test_limit_runtime()
        finally:
            app_settings.TIMEOUT_LIMIT = _timeout

    def test_wrong_timeout_value(self):
        _timeout = app_settings.TIMEOUT_LIMIT
        try:
            app_settings.TIMEOUT_LIMIT = "foo"  # type: ignore[assignment]
            with pytest.raises(ValueError, match="invalid literal for int()"):
                CrawlManager(self.spider.name, self.kwargs.copy())
        finally:
            app_settings.TIMEOUT_LIMIT = _timeout


class TestHandleSpiderError(TestCrawlManager):
    def setUp(self):
        super().setUp()
        self.exception_message = "Foo"
        self.exception = Exception(self.exception_message)
        self.failure = Failure(self.exception)

    def test_handle_spider_error_debug_true(self):
        assert len(self.crawl_manager.errors) == 0
        self.crawl_manager.handle_spider_error(self.failure, self.spider)
        assert len(self.crawl_manager.errors) == 1
        assert "Traceback" in self.crawl_manager.errors[0]
        assert self.exception.__class__.__name__ in self.crawl_manager.errors[0]
        assert self.exception_message in self.crawl_manager.errors[0]

    def test_handle_spider_error_debug_false(self):
        self.crawl_manager.debug = False
        assert len(self.crawl_manager.errors) == 0
        self.crawl_manager.handle_spider_error(self.failure, self.spider)
        assert len(self.crawl_manager.errors) == 0

    def test_handle_spider_error_another_spider(self):
        assert len(self.crawl_manager.errors) == 0
        self.crawl_manager.handle_spider_error(self.failure, self.another_spider)
        assert len(self.crawl_manager.errors) == 0


class TestLimitRequests(TestCrawlManager):
    def test_max_requests_not_set(self):
        for _i in range(100):
            self.crawl_manager.limit_requests(self.spider)
        assert not self.crawler.engine.close_spider.called

    def test_max_requests_set(self):
        self.crawl_manager.max_requests = 10
        for _i in range(self.crawl_manager.max_requests):
            self.crawl_manager.limit_requests(self.spider)
        assert not self.crawler.engine.close_spider.called
        self.crawl_manager.limit_requests(self.spider)
        assert self.crawler.engine.close_spider.called


class TestGetItem(TestCrawlManager):
    def setUp(self):
        super().setUp()
        self.item = Item()

    def test_get_item(self):
        assert len(self.crawl_manager.items) == 0
        self.crawl_manager.get_item(self.item, self.response, self.spider)
        assert len(self.crawl_manager.items) == 1
        assert self.crawl_manager.items[0] == self.item

    def test_get_item_another_spider(self):
        assert len(self.crawl_manager.items) == 0
        self.crawl_manager.get_item(self.item, self.response, self.another_spider)
        assert len(self.crawl_manager.items) == 0


class TestCollectDropped(TestCrawlManager):
    def setUp(self):
        super().setUp()
        self.exception = Exception("foo")
        self.expected_result = {
            "item": self.item,
            "response": self.response,
            "exception": str(self.exception),
        }

    def test_collect_dropped(self):
        assert len(self.crawl_manager.items_dropped) == 0
        self.crawl_manager.collect_dropped(
            self.item,
            self.response,
            self.exception,
            self.spider,
        )
        assert len(self.crawl_manager.items_dropped) == 1
        assert len(self.crawl_manager.items_dropped) == 1
        assert self.crawl_manager.items_dropped[0] == self.expected_result

    def test_collect_dropped_another_spider(self):
        assert len(self.crawl_manager.items_dropped) == 0
        self.crawl_manager.collect_dropped(
            self.item,
            self.response,
            self.exception,
            self.another_spider,
        )
        assert len(self.crawl_manager.items_dropped) == 0


class TestReturnItems(TestCrawlManager):
    def setUp(self):
        super().setUp()
        self.stats = {
            "log_count/INFO": 6,
            "scheduler/enqueued/memory": 4,
            "scheduler/dequeued/memory": 4,
        }
        self.crawl_manager.crawler = MagicMock()
        self.crawl_manager.crawler.stats.get_stats.return_value = self.stats
        self.expected_result = {
            "items": self.crawl_manager.items,
            "items_dropped": self.crawl_manager.items_dropped,
            "stats": self.stats.copy(),
            "spider_name": self.spider.name,
            "user_error": None,
        }

    def test_return_items(self):
        result = self.crawl_manager.return_items(None)
        assert dict(result, **self.expected_result) == result
        assert sorted(self.stats.keys()) == list(result["stats"].keys())
        # debug = True by default
        assert "errors" in result
        assert result["errors"] == self.crawl_manager.errors

    def test_return_items_without_debug(self):
        self.crawl_manager.debug = False
        result = self.crawl_manager.return_items(None)
        assert self.expected_result == result
        assert "errors" not in result


class TestCreateSpiderRequest(TestCrawlManager):
    def test_valid_arguments(self):
        req = self.crawl_manager.create_spider_request(self.kwargs)
        assert req.dont_filter
        assert req.url == self.url

    def test_invalid_arguments(self):
        self.kwargs["url1"] = "http://localhost/foo"
        with pytest.raises(Error) as exception:
            self.crawl_manager.create_spider_request(self.kwargs)
        assert exception.value.status == b"400"

    def test_invalid_url(self):
        self.kwargs["url"] = "//localhost/foo"
        with pytest.raises(Error) as exception:
            self.crawl_manager.create_spider_request(self.kwargs)
        assert exception.value.status == b"400"
        self.kwargs["url"] = "localhost/foo"
        with pytest.raises(Error) as exception:
            self.crawl_manager.create_spider_request(self.kwargs)
        assert exception.value.status == b"400"


class TestCreateProperLogFile(TestCrawlManager):
    def test_filename(self):
        self.crawl_manager.log_dir = Path("some_dir_name")
        path = self.crawl_manager._get_log_file_path()
        filename = Path(path).name
        expected_format = "%Y-%m-%dT%H%M%S.%f.log"
        datetime_object = dt.datetime.strptime(filename, expected_format)
        now = dt.datetime.now()
        assert datetime_object
        delta = now - datetime_object
        assert delta.seconds < 60
