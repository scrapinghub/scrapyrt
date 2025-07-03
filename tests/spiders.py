from __future__ import annotations

from scrapy import Request, Spider


class MetaSpider(Spider):
    """Copy-paste from scrapy tests."""

    name = "meta"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.meta = {}

    def closed(self, reason):
        self.meta["close_reason"] = reason


class SingleRequestSpider(MetaSpider):
    """Copy-paste from scrapy tests."""

    seed: Request | str | None = None
    callback_func = None
    errback_func = None
    name = "single_request"

    def start_requests(self):
        if isinstance(self.seed, Request):
            yield self.seed.replace(callback=self.parse, errback=self.on_error)
        else:
            assert self.seed is not None
            yield Request(self.seed, callback=self.parse, errback=self.on_error)

    def parse(self, response):
        self.meta.setdefault("responses", []).append(response)
        if callable(self.callback_func):
            return self.callback_func(response)
        if "next" in response.meta:
            return response.meta["next"]
        return None

    def on_error(self, failure):
        self.meta["failure"] = failure
        if callable(self.errback_func):
            return self.errback_func(failure)
        return None
