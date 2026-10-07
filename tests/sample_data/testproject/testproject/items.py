import scrapy


class TestprojectItem(scrapy.Item):
    name = scrapy.Field()
    referer = scrapy.Field()
    response = scrapy.Field()
