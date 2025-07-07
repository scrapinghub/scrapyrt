import os
import shutil
from pathlib import Path

from scrapy.settings import Settings, default_settings

from . import PROJECT_PATH, SAMPLE_DATA

ASYNCIO_REACTOR_IS_DEFAULT = (
    default_settings.TWISTED_REACTOR
    == "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
)
LOCALHOST = "localhost"


def get_testenv():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_PATH)
    return env


def get_settings():
    """Settings with all extensions disabled."""
    return Settings(
        {
            "EXTENSIONS": {
                "scrapy.extensions.throttle.AutoThrottle": None,
                "scrapy.extensions.feedexport.FeedExporter": None,
                "scrapy.extensions.logstats.LogStats": None,
                "scrapy.extensions.closespider.CloseSpider": None,
                "scrapy.extensions.corestats.CoreStats": None,
                "scrapy.extensions.memusage.MemoryUsage": None,
                "scrapy.extensions.memdebug.MemoryDebugger": None,
                "scrapy.extensions.spiderstate.SpiderState": None,
                "scrapy.extensions.telnet.TelnetConsole": None,
            }
        }
    )


def generate_project(directory: Path, site=None):
    source = SAMPLE_DATA / "testproject"
    shutil.copytree(source, directory, ignore=shutil.ignore_patterns("*.pyc"))
    # Pass site url to spider doing start requests
    spider_name = "testspider_startrequests.py.jinja"
    spider_filename = directory / "testproject" / "spider_templates" / spider_name
    spider_target_place = directory / "testproject" / "spiders" / spider_name
    if not site:
        return
    spider_string = spider_filename.read_text().format(
        site.url("page1.html"), site.url("page2.html")
    )
    with spider_target_place.open("wb") as output:
        output.write(spider_string.encode("utf-8"))
