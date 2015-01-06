# -*- coding: utf-8 -*-
import scrapy

from ..items import TestprojectItem


class TestSpider(scrapy.Spider):

    name = 'test'

    def parse(self, response):
        name = response.xpath('//h1/text()').extract()
        return TestprojectItem(name=name)
