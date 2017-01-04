# coding: utf8

# Have `logging` patched before scrapyrt is loaded, since scrapyrt loads
# scrapy very early, which makes it hard to patch it when loading our
# customizations, e.g. CrawlResource

import logging
import inspect


def patch_logging():
    """Have `logging.getLogger` patched"""
    old_get_logger = logging.getLogger

    def get_logger(*args, **kwargs):
        logger = old_get_logger(*args, **kwargs)
        logger.__class__ = ScrapyRTLogger
        return logger

    logging.getLogger = get_logger


class ScrapyRTLogger(logging.Logger):

    def handle(self, record):
        """Handles a logging record"""
        ret = super(ScrapyRTLogger, self).handle(record)
        stack = inspect.stack()
        if self._is_error(stack, record):
            crawler = self._get_crawler(stack)
            import scrapyrt.core
            assert isinstance(crawler, scrapyrt.core.ScrapyrtCrawler)
            crawler.errors.append(record.getMessage())
        return ret

    def _is_error(self, stack, record):
        """Returns whether we have an error here"""
        if record.levelno >= logging.ERROR:
            return True
        if any(
                '/scrapy/spidermiddlewares/httperror.py' in x[1]
                for x in stack):
            # HttpErrorMiddleware logs to DEBUG, but that kind of log looks
            # important to us as well.
            return True
        if record.msg.startswith('Error'):
            # There are several such logs, e.g. `logger.info('Error ...')`
            return True
        return False

    def _get_crawler(self, stack):
        """Returns a cralwer instance found from the stack, or None"""
        for record in stack:
            frame, path = record[:2]
            if '/scrapy/' in path:
                for key, value in frame.f_locals.items():
                    crawler = self._get_crawler_from_obj(value)
                    if crawler:
                        return crawler

    def _get_crawler_from_obj(self, obj):
        """Returns a cralwer instance found from the object, or None"""
        # WARNING: Do not import any Scrapy package too early
        import scrapy.crawler
        if isinstance(obj, scrapy.crawler.Crawler):
            return obj
        if getattr(obj, 'crawler', None):
            crawler = self._get_crawler_from_obj(obj.crawler)
            if crawler:
                return crawler
        if getattr(obj, 'spider', None):
            crawler = self._get_crawler_from_obj(obj.spider)
            if crawler:
                return crawler
        return None


# WARNING: Do not import any Scrapy-related packages above this line
