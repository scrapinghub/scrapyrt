from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
import datetime
import os
import traceback

from packaging.version import Version
from scrapy import signals, Spider
from scrapy.crawler import CrawlerRunner, Crawler
from scrapy.exceptions import DontCloseSpider
from scrapy.http import Request
from twisted.web.error import Error
from twisted.internet import defer

from . import log
from .conf import app_settings
from .conf.spider_settings import get_scrapyrt_settings, get_project_settings
from .decorators import deprecated
from .log import setup_spider_logging


class ScrapyrtCrawlerRunner(CrawlerRunner):

    def __init__(self, settings, scrapyrt_manager):
        super(ScrapyrtCrawlerRunner, self).__init__(settings)
        self.scrapyrt_manager = scrapyrt_manager

    def create_crawler(
        self, crawler_or_spidercls: type[Spider] | str | Crawler
    ) -> Crawler:
        crawler = super().create_crawler(crawler_or_spidercls)
        self.scrapyrt_manager.crawler = crawler
        crawler.signals.connect(self.scrapyrt_manager.get_item,
                                signals.item_scraped)
        crawler.signals.connect(self.scrapyrt_manager.collect_dropped,
                                signals.item_dropped)
        crawler.signals.connect(self.scrapyrt_manager.spider_idle,
                                signals.spider_idle)
        crawler.signals.connect(self.scrapyrt_manager.handle_spider_error,
                                signals.spider_error)
        crawler.signals.connect(self.scrapyrt_manager.handle_scheduling,
                                signals.request_scheduled)
        crawler.signals.connect(self.scrapyrt_manager.read_spider,
                                signals.spider_opened)
        return crawler


class CrawlManager(object):
    """
    Runs crawls
    """

    def __init__(self, spider_name, request_kwargs,
                 max_requests=None, start_requests=False):
        self.spider_name = spider_name
        self.log_dir = app_settings.LOG_DIR
        self.items = []
        self.items_dropped = []
        self.errors = []
        self.user_error = None
        self.max_requests = int(max_requests) if max_requests else None
        self.timeout_limit = int(app_settings.TIMEOUT_LIMIT)
        self.request_count = 0
        self.debug = app_settings.DEBUG
        self.crawler_runner = None
        self.crawler = None
        self.crawl_start_time = datetime.datetime.utcnow()
        # callback will be added after instantiation of crawler object
        # because we need to know if spider has method available
        self.callback_name = request_kwargs.pop('callback', None) or 'parse'
        # do the same for errback
        self.errback_name = request_kwargs.pop('errback', None) or app_settings.DEFAULT_ERRBACK_NAME

        if request_kwargs.get("url"):
            self.request = self.create_spider_request(deepcopy(request_kwargs))
        else:
            self.request = None
        self.start_requests = start_requests
        self._request_scheduled = False
        self.original_start_methods = {}

    def crawl(self, *args, **kwargs):
        settings = self.get_project_settings()
        self.crawler_runner = ScrapyrtCrawlerRunner(settings, self)
        spidercls = self.crawler_runner.spider_loader.load(self.spider_name)
        for kw in kwargs:
            attr_or_m = getattr(spidercls, kw, None)
            if attr_or_m and callable(attr_or_m):
                msg = 'Crawl argument cannot override spider method.'
                msg += ' Got argument {} that overrides spider method {}'
                raise Error('400', message=msg.format(kw, getattr(spidercls, kw)))
        if not self.start_requests:
            self.set_dummy_start_methods(spidercls)
        dfd = self.crawler_runner.crawl(spidercls, *args, **kwargs)
        def cleanup_logging(result):
            if hasattr(self, '_cleanup_handler'):
                self._cleanup_handler()
            return result
        dfd.addBoth(self.restore_start_methods)
        dfd.addBoth(cleanup_logging)
        dfd.addCallback(self.return_items)
        return dfd

    def set_dummy_start_methods(self, spidercls):
        if hasattr(spidercls, "start"):
            async def dummy_start(*args, **kwargs):
                return
                yield
            self.original_start_methods['start'] = spidercls.start
            spidercls.start = dummy_start
        if hasattr(spidercls, "start_requests"):
            def dummy_start_requests(*args, **kwargs):
                return
                yield
            self.original_start_methods['start_requests'] = spidercls.start_requests
            spidercls.start_requests = dummy_start_requests

    def restore_start_methods(self, result):
        for method_name in list(self.original_start_methods):
            original_method = self.original_start_methods.pop(method_name)
            setattr(self.crawler.spider.__class__, method_name, original_method)
        return result

    def read_spider(self, spider):
        self._cleanup_handler = setup_spider_logging(spider, spider.settings)

    def _get_log_file_path(self):
        log_dir = os.path.join(self.log_dir, self.spider_name)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        time_format = app_settings.SPIDER_LOG_FILE_TIMEFORMAT
        filename = datetime.datetime.now().strftime(time_format) + '.log'
        return os.path.join(log_dir, filename)

    def get_project_settings(self):
        # set logfile for a job
        log_file = self._get_log_file_path()
        custom_settings = get_scrapyrt_settings(log_file=log_file)
        return get_project_settings(custom_settings=custom_settings)

    @deprecated(use_instead='.crawl()')
    def create_crawler(self, **kwargs):
        return self.crawl()

    def spider_idle(self, spider):
        """Handler of spider_idle signal.

        Schedule request for url given to api, with optional callback
        and errback that can be passed as GET parameter.

        spider_idle signal is used because we want to optionally enable
        start_requests for the spider and if request is scheduled in
        spider_opened signal handler it's fired earlier then start_requests
        which is totally wrong.

        """
        if spider is self.crawler.spider and self.request and not self._request_scheduled:
            try:
                callback = getattr(self.crawler.spider, self.callback_name)
                assert callable(callback), 'Invalid callback'
                self.request = self.request.replace(callback=callback)
            except (AssertionError, AttributeError):
                msg = f"Invalid spider callback {self.callback_name}, callback not callable or not a method of a spider {self.spider_name}"
                self.user_error = Error(400, message=msg)
            try:
                if self.errback_name:
                    errback = getattr(self.crawler.spider, self.errback_name)
                    assert callable(errback), 'Invalid errback'
                    self.request = self.request.replace(errback=errback)
            except (AssertionError, AttributeError):
                msg = f"Invalid spider errback {self.errback_name}, errback not callable or not a method of a spider {self.spider_name}"
                self.user_error = Error(400, message=msg)
            if self.user_error:
                log.msg(self.user_error.message, level=log.ERROR)
                return

            modify_request = getattr(
                self.crawler.spider, "modify_realtime_request", None)
            if callable(modify_request):
                self.request = modify_request(self.request)

            spider.crawler.engine.crawl(self.request)
            self._request_scheduled = True
            raise DontCloseSpider

    def handle_scheduling(self, request, spider):
        """Handler of request_scheduled signal.

        For every scheduled request check if number of requests is less
        then limit and runtime doesn't exceed limit as well.

        """
        if spider is self.crawler.spider:
            self.limit_requests(spider)
            self.limit_runtime(spider)

    def limit_runtime(self, spider):
        """Stop crawl if it takes too long."""
        time_now = datetime.datetime.utcnow()
        if (time_now - self.crawl_start_time).seconds >= self.timeout_limit:
            spider.crawler.engine.close_spider(spider, reason="timeout")

    def limit_requests(self, spider):
        """Stop crawl after reaching max_requests."""
        if self.max_requests and self.max_requests <= self.request_count:
            reason = "stop generating requests, only {} requests allowed".format(
                self.max_requests)
            spider.crawler.engine.close_spider(spider, reason=reason)
        else:
            self.request_count += 1

    def handle_spider_error(self, failure, spider):
        if spider is self.crawler.spider and self.debug:
            fail_data = failure.getTraceback()
            self.errors.append(fail_data)

    def get_item(self, item, response, spider):
        if spider is self.crawler.spider:
            self.items.append(item)

    def collect_dropped(self, item, response, exception, spider):
        if spider is self.crawler.spider:
            self.items_dropped.append({
                "item": item,
                "exception": str(exception),
                "response": response
            })

    def return_items(self, result):
        stats = self.crawler.stats.get_stats()
        stats = OrderedDict((k, v) for k, v in sorted(stats.items()))
        results = {
            "items": self.items,
            "items_dropped": self.items_dropped,
            "stats": stats,
            "spider_name": self.spider_name,
        }

        results["user_error"] = self.user_error

        if self.debug:
            results["errors"] = self.errors
        return results

    def create_spider_request(self, kwargs):
        url = kwargs.pop('url')
        try:
            req = Request(url, **kwargs)
        except (TypeError, ValueError) as e:
            msg = "Error while creating Scrapy Request, {}"
            message = msg.format(str(e))
            raise Error('400', message=message)

        req.dont_filter = True
        msg = u"Created request for spider {} with url {} and kwargs {}"
        msg = msg.format(self.spider_name, url, repr(kwargs))
        log.msg(msg)
        return req
