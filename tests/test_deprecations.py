import pytest

from scrapyrt.core import CrawlManager


def test_crawl_manager_start_requests():
    with pytest.warns(
        DeprecationWarning,
        match=r"The start_requests parameter of CrawlManager\(\) is deprecated",
    ):
        CrawlManager("foo", {}, start_requests=False)
    with pytest.warns(
        DeprecationWarning,
        match=r"The start_requests parameter of CrawlManager\(\) is deprecated",
    ):
        CrawlManager("foo", {}, start_requests=True)

    manager = CrawlManager("foo", {})
    with pytest.warns(
        DeprecationWarning,
        match=r"CrawlManager\.start_requests is deprecated",
    ):
        manager.start_requests = False
    with pytest.warns(
        DeprecationWarning,
        match=r"CrawlManager\.start_requests is deprecated",
    ):
        manager.start_requests = True
    with pytest.warns(
        DeprecationWarning,
        match=r"CrawlManager\.start_requests is deprecated",
    ):
        _ = manager.start_requests
    with pytest.warns(
        DeprecationWarning,
        match=r"CrawlManager\.start_requests is deprecated",
    ):
        _ = manager.start_requests

    class CustomCrawlManager(CrawlManager):
        def __init__(self):
            super().__init__("foo", {})
            self.start_requests = False

    with pytest.warns(
        DeprecationWarning,
        match=r"CrawlManager\.start_requests is deprecated",
    ):
        CustomCrawlManager()
