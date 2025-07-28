from pathlib import Path
from shutil import copytree, ignore_patterns
from typing import Any

import pytest
from packaging.version import Version

from tests import SAMPLE_DATA
from tests.servers import MockServer, ScrapyrtTestServer
from tests.test_resource_crawl import perform_get, perform_post
from tests.utils import SCRAPY_VERSION


def generate_spider_start_project(root: Path, site):
    source = SAMPLE_DATA / "spider-start-project"
    copytree(source, root, ignore=ignore_patterns("*.pyc"), dirs_exist_ok=True)
    for spider in ("new", "universal", "old"):
        spider_path = root / "project" / "spiders" / f"{spider}.py"
        content = spider_path.read_text()
        for page_number, subdomain in enumerate(("start", "start_requests"), start=1):
            placeholder_url = f"https://{subdomain}.example"
            actual_url = f"{site.url(f'page{page_number}.html')}"
            content = content.replace(placeholder_url, actual_url)
        spider_path.write_text(content)


@pytest.fixture
def server():
    site = MockServer()
    site.start()
    server = ScrapyrtTestServer(
        site=site,
        project_generator=generate_spider_start_project,
    )
    server.start()
    yield server
    server.stop()
    site.stop()


@pytest.mark.parametrize(
    ("spider", "start_param"),
    (
        ("new", "spider_start"),
        ("new", "start_requests"),
        ("new", None),
        ("universal", "spider_start"),
        ("universal", "start_requests"),
        ("universal", None),
        ("old", "spider_start"),
        ("old", "start_requests"),
        ("old", None),
    ),
)
@pytest.mark.parametrize("method", (perform_get, perform_post))
def test(server, spider, start_param, method):
    kwargs: dict[str, Any] = {"spider_name": spider}
    if start_param:
        kwargs[start_param] = True
    response = method(
        server.url("crawl.json"),
        kwargs,
        {"url": f"{server.site.url('page3.html')}"},
    )
    assert response.status_code == 200
    data = response.json()
    actual_urls = {item["url"] for item in data["items"]}
    expected_pages = {3}
    if start_param:
        if spider != "old" and Version("2.13") <= SCRAPY_VERSION:
            expected_pages.add(1)
        if spider == "old" or (
            spider == "universal" and Version("2.13") > SCRAPY_VERSION
        ):
            expected_pages.add(2)
    expected_urls = {f"{server.site.url(f'page{n}.html')}" for n in expected_pages}
    assert expected_urls == actual_urls
    if start_param == "start_requests":
        assert data["warnings"] == [
            "The start_requests parameter is deprecated, use spider_start instead.",
        ]
    assert data.get("errors") is None
