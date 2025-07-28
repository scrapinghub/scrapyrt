from pathlib import Path

from scrapy.utils.reactor import install_reactor

from scrapyrt.conf import app_settings

if app_settings.TWISTED_REACTOR is not None:
    install_reactor(app_settings.TWISTED_REACTOR)

TESTS_PATH = Path(__file__).resolve().parent
PROJECT_PATH = TESTS_PATH.parent
SAMPLE_DATA = TESTS_PATH / "sample_data"
