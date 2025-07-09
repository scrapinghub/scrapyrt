from packaging.version import Version
from scrapy import __version__ as scrapy_version

BOT_NAME = "testproject"

SPIDER_MODULES = ["testproject.spiders"]
NEWSPIDER_MODULE = "testproject.spiders"

if Version(scrapy_version) < Version("2.12"):
    REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
