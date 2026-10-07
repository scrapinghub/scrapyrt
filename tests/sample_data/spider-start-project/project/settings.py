from packaging.version import Version
from scrapy import __version__ as SCRAPY_VERSION

SPIDER_MODULES = ["project.spiders"]

if Version(SCRAPY_VERSION) < Version("2.12"):
    REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
