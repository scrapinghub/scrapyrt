# -*- coding: utf-8 -*-
import scrapy

from ..items import TestprojectItem


class TestSpider(scrapy.Spider):

    name = 'test_with_sr'
    initial_urls = ["{0}", "{1}"]

    def start_requests(self):
        for url in self.initial_urls:
            yield scrapy.Request(url, callback=self.some_callback, meta=dict(referer=url))

    def some_callback(self, response):
        name = response.xpath('//h1/text()').extract()
        return TestprojectItem(name=name, referer=response.meta["referer"])

    def parse(self, response):
        name = response.xpath("//h1/text()").extract()
        return TestprojectItem(name=name, referer=response.meta.get("referer"),
                               response=response.url)