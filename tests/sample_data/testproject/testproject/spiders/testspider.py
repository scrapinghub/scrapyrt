# -*- coding: utf-8 -*-
import scrapy

from ..items import TestprojectItem


class TestSpider(scrapy.Spider):

    name = 'test'

    def parse(self, response):
        name = response.xpath('//h1/text()').extract()
        return TestprojectItem(name=name)

    def return_bytes(self, response):
        return TestprojectItem(name=b'Some bytes here')

    def some_errback(self, err):
        self.logger.error("Logging some error {}".format(err))
        return
