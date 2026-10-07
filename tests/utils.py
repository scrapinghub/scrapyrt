import os
import shutil
from pathlib import Path
from typing import Any

from packaging.version import Version
from scrapy import __version__ as scrapy_version
from scrapy.settings import Settings, default_settings

from . import PROJECT_PATH, SAMPLE_DATA

ASYNCIO_REACTOR_IS_DEFAULT = (
    default_settings.TWISTED_REACTOR
    == "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
)
LOCALHOST = "localhost"
SCRAPY_VERSION = Version(scrapy_version)
REQUEST_FINGERPRINTER_IMPLEMENTATION_IS_DEPRECATED = Version("2.12") <= SCRAPY_VERSION


def get_testenv():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_PATH)
    return env


def get_settings():
    """Settings with all extensions disabled."""
    settings: dict[str, Any] = {
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
        },
    }
    if not REQUEST_FINGERPRINTER_IMPLEMENTATION_IS_DEPRECATED:
        settings["REQUEST_FINGERPRINTER_IMPLEMENTATION"] = "2.7"
    return Settings(settings)


def generate_project(directory: Path, site=None):
    source = SAMPLE_DATA / "testproject"
    shutil.copytree(
        source,
        directory,
        ignore=shutil.ignore_patterns("*.pyc"),
        dirs_exist_ok=True,
    )
    # Pass site url to spider doing start requests
    spider_filename = (
        directory
        / "testproject"
        / "spider_templates"
        / "testspider_startrequests.py.jinja"
    )
    spider_target_place = (
        directory / "testproject" / "spiders" / "testspider_startrequests.py"
    )
    if not site:
        return
    spider_string = spider_filename.read_text().format(
        site.url("page1.html"),
        site.url("page2.html"),
    )
    with spider_target_place.open("wb") as output:
        output.write(spider_string.encode("utf-8"))
