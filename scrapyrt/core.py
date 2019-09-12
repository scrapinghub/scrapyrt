# -*- coding: utf-8 -*-
from collections import OrderedDict
from copy import deepcopy
import datetime
import os
import six

from scrapy import signals
from scrapy.crawler import CrawlerRunner, Crawler
from scrapy.exceptions import DontCloseSpider
from scrapy.http import Request
from twisted.web.error import Error
from twisted.internet import defer

from . import log
from .conf import settings
from .conf.spider_settings import get_scrapyrt_settings, get_project_settings
from .decorators import deprecated
from .log import setup_spider_logging


class ScrapyrtCrawler(Crawler):
    """Main and only difference from base class -
    ScrapyrtCrawler allows us to call or not call
    start_requests.

    https://github.com/scrapy/scrapy/blob/master/scrapy/crawler.py#L52

    TODO: PR to scrapy - ability to set start_requests here.

    """
    def __init__(self, spidercls, crawler_settings, start_requests=False):
        super(ScrapyrtCrawler, self).__init__(spidercls, crawler_settings)
        self.start_requests = start_requests

    @defer.inlineCallbacks
    def crawl(self, *args, **kwargs):
        assert not self.crawling, "Crawling already taking place"
        self.crawling = True
        try:
            self.spider = self._create_spider(*args, **kwargs)
            self.engine = self._create_engine()
            if self.start_requests:
                start_requests = iter(self.spider.start_requests())
            else:
                start_requests = ()
            yield self.engine.open_spider(self.spider, start_requests)
            yield defer.maybeDeferred(self.engine.start)
        except Exception:
            self.crawling = False
            raise


class ScrapyrtCrawlerProcess(CrawlerRunner):

    def __init__(self, settings, scrapyrt_manager):
        super(ScrapyrtCrawlerProcess, self).__init__(settings)
        self.scrapyrt_manager = scrapyrt_manager

    def crawl(self, spidercls, *args, **kwargs):
        if isinstance(spidercls, six.string_types):
            spidercls = self.spider_loader.load(spidercls)
        # creating our own crawler that will allow us to disable start requests easily
        crawler = ScrapyrtCrawler(
            spidercls, self.settings, self.scrapyrt_manager.start_requests)
        self.scrapyrt_manager.crawler = crawler
        # Connecting signals to handlers that control crawl process
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
        dfd = super(ScrapyrtCrawlerProcess, self).crawl(crawler, *args, **kwargs)
        _cleanup_handler = setup_spider_logging(crawler.spider, self.settings)

        def cleanup_logging(result):
            _cleanup_handler()
            return result

        return dfd.addBoth(cleanup_logging)


class CrawlManager(object):
    """
    Runs crawls
    """

    def __init__(self, spider_name, request_kwargs, max_requests=None, start_requests=False):
        self.spider_name = spider_name
        self.log_dir = settings.LOG_DIR
        self.items = []
        self.items_dropped = []
        self.errors = []
        self.max_requests = int(max_requests) if max_requests else None
        self.timeout_limit = int(settings.TIMEOUT_LIMIT)
        self.request_count = 0
        self.debug = settings.DEBUG
        self.crawler_process = None
        self.crawler = None
        # callback will be added after instantiation of crawler object
        # because we need to know if spider has method available
        self.callback_name = request_kwargs.pop('callback', None) or 'parse'
        if request_kwargs.get("url"):
            self.request = self.create_spider_request(deepcopy(request_kwargs))
        else:
            self.request = None
        self.start_requests = start_requests
        self._request_scheduled = False

    def crawl(self, *args, **kwargs):
        self.crawler_process = ScrapyrtCrawlerProcess(
            self.get_project_settings(), self)
        try:
            dfd = self.crawler_process.crawl(self.spider_name, *args, **kwargs)
        except KeyError as e:
            # Spider not found.
            raise Error('404', message=str(e))
        dfd.addCallback(self.return_items)
        return dfd

    def _get_log_file_path(self):
        log_dir = os.path.join(self.log_dir, self.spider_name)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        time_format = settings.SPIDER_LOG_FILE_TIMEFORMAT
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
        that can be passed as GET parameter.

        spider_idle signal is used because we want to optionally enable
        start_requests for the spider and if request is scheduled in
        spider_opened signal handler it's fired earlier then start_requests
        which is totally wrong.

        """
        if spider is self.crawler.spider and self.request and not self._request_scheduled:
            callback = getattr(self.crawler.spider, self.callback_name)
            assert callable(callback), 'Invalid callback'
            self.request = self.request.replace(callback=callback)
            modify_request = getattr(
                self.crawler.spider, "modify_realtime_request", None)
            if callable(modify_request):
                self.request = modify_request(self.request)
            spider.crawler.engine.crawl(self.request, spider)
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
        start_time = self.crawler.stats.get_value("start_time")
        time_now = datetime.datetime.utcnow()
        if (time_now - start_time).seconds >= self.timeout_limit:
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
