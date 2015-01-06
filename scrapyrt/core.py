# -*- coding: utf-8 -*-
from collections import OrderedDict
from copy import deepcopy
import os
import datetime
from twisted.web.error import Error
from twisted.internet import defer
import six


from scrapy import signals
from scrapy.crawler import CrawlerProcess, Crawler
from scrapy.http import Request

from . import log
from .conf import settings
from .conf.spider_settings import get_scrapyrt_settings, get_project_settings


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


class ScrapyrtCrawlerProcess(CrawlerProcess):

    def __init__(self, settings, scrapyrt_manager):
        super(ScrapyrtCrawlerProcess, self).__init__(settings)
        self.scrapyrt_manager = scrapyrt_manager

    def _create_crawler(self, spidercls):
        if isinstance(spidercls, six.string_types):
            spidercls = self.spiders.load(spidercls)

        crawler_settings = self.settings.copy()
        spidercls.update_settings(crawler_settings)
        crawler_settings.freeze()

        # creating our own crawler that will allow us to disable
        # start requests easily
        # TODO: PR to scrapy - set custom Crawler
        crawler = ScrapyrtCrawler(spidercls, crawler_settings)
        self.scrapyrt_manager.crawler = crawler
        # Connecting signals to handlers that control crawl process
        crawler.signals.connect(self.scrapyrt_manager.get_item,
                                signals.item_scraped)
        crawler.signals.connect(self.scrapyrt_manager.collect_dropped,
                                signals.item_dropped)
        crawler.signals.connect(self.scrapyrt_manager.spider_opened,
                                signals.spider_opened)
        crawler.signals.connect(self.scrapyrt_manager.handle_spider_error,
                                signals.spider_error)
        crawler.signals.connect(self.scrapyrt_manager.handle_scheduling,
                                signals.request_scheduled)
        return crawler


class CrawlManager(object):
    """
    Runs crawls
    """

    def __init__(self, spider_name, request_kwargs, max_requests=None):
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
        self.request = self.create_spider_request(deepcopy(request_kwargs))

    def crawl(self):
        dfd = self.create_crawler(self.get_project_settings())
        dfd.addCallback(self.return_items)
        return dfd

    def _get_log_file_path(self):
        log_dir = os.path.join(self.log_dir, self.spider_name)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        filename = datetime.datetime.now().isoformat() + '.log'
        return os.path.join(log_dir, filename)

    def get_project_settings(self):
        # set logfile for a job
        log_file = self._get_log_file_path()
        custom_settings = get_scrapyrt_settings(log_file=log_file)
        return get_project_settings(custom_settings=custom_settings)

    def create_crawler(self, settings, **kwargs):
        self.crawler_process = ScrapyrtCrawlerProcess(settings, self)
        try:
            dfd = self.crawler_process.crawl(self.spider_name, **kwargs)
        except KeyError as e:
            # spider not found
            raise Error('404', message=e.message)
        return dfd

    def spider_opened(self, spider):
        """Handler of spider_opened signal.

        Schedule request for url given to api, with optional callback
        that can be passed as GET parameter.

        """
        if spider is self.crawler.spider:
            # Need to update request here because spider_opened is called
            # inside Crawler.crawl and it's hard to intercept flow
            # in other places.
            callback = getattr(self.crawler.spider, self.callback_name)
            assert callable(callback), 'Invalid callback'
            self.request = self.request.replace(callback=callback)
            modify_request = getattr(
                self.crawler.spider, "modify_realtime_request", None)
            if callable(modify_request):
                self.request = modify_request(self.request)
            spider.crawler.engine.schedule(self.request, spider)

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
            reason = "stop generating requests, only one request allowed"
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
                "exception": exception.message,
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
            # Bad arguments for scrapy Request
            # we don't want to schedule spider if someone
            # passes meaingless arguments to Request.
            # We must raise this here so that this will be returned to client,
            # Otherwise if this is raised in spider_opened it goes to
            # spider logs where it does not really belong.
            # It is needed because in POST handler we can pass
            # all possible requests kwargs, so it is easy to make mistakes.
            message = "Error while creating Request, {}".format(e.message)
            raise Error('400', message=message)

        req.dont_filter = True
        msg = u"Created request for spider {} with url {} and kwargs {}"
        msg = msg.format(self.spider_name, url, repr(kwargs))
        log.msg(msg)
        return req
