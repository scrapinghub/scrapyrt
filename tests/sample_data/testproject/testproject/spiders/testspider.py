import scrapy

from ..items import TestprojectItem


class TestSpider(scrapy.Spider):
    name = "test"
    some_attribute = "Yes|No"
    postcode: str

    def parse(self, response):
        name = response.xpath("//h1/text()").extract()
        return TestprojectItem(name=name)

    def return_bytes(self, response):
        return TestprojectItem(name=b"Some bytes here")

    def some_errback(self, err):
        self.logger.error(f"Logging some error {err}")

    def return_argument(self, response):
        return TestprojectItem(name=self.postcode)
