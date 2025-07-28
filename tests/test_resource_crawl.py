import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, patch
from urllib.parse import quote

import pytest
import requests
from twisted.trial import unittest
from twisted.web.error import Error
from twisted.web.server import Request

from scrapyrt.resources import CrawlResource

from .servers import MockServer, ScrapyrtTestServer


@pytest.fixture
def server(request):
    site = MockServer()
    site.start()
    server = ScrapyrtTestServer(site=site)
    server.start()
    yield server
    server.stop()
    site.stop()


@pytest.fixture
def t_req():
    return MagicMock(spec=Request)


@pytest.fixture
def resource():
    return CrawlResource()


class TestCrawlResource:
    def test_is_leaf(self):
        assert CrawlResource.isLeaf

    def test_render_GET(self, t_req, resource):
        t_req.args = {b"url": [b"http://foo"], b"spider_name": [b"test"]}
        resource.validate_options = Mock()

        with patch("scrapyrt.core.CrawlManager", spec=True) as manager:
            instance = manager.return_value
            resource.render_GET(t_req)
        scrapy_params = {"url": "http://foo"}
        api_params = {"spider_name": "test", "url": "http://foo"}
        resource.validate_options.assert_called_once_with(scrapy_params, api_params)
        assert instance.crawl.called

    def test_render_POST(self, t_req, resource):
        t_req.content.getvalue.return_value = json.dumps(
            {"spider_name": "test", "request": {"url": "http://foo.com"}},
        )
        resource.validate_options = Mock()
        with patch("scrapyrt.core.CrawlManager", spec=True) as manager:
            instance = manager.return_value
            resource.render_POST(t_req)

        scrapy_params = {"url": "http://foo.com"}
        api_params = {"request": {"url": "http://foo.com"}, "spider_name": "test"}
        assert instance.crawl.called
        resource.validate_options.assert_called_once_with(scrapy_params, api_params)

    def test_render_POST_invalid_json(self, t_req, resource):
        t_req.content.getvalue.return_value = b"{{{{{"
        with (
            patch("scrapyrt.core.CrawlManager", spec=True) as manager,
            pytest.raises(Error) as e,
        ):
            resource.render_POST(t_req)
        assert e.value.status == b"400"
        assert e.value.message
        assert re.search(b"Invalid JSON in POST", e.value.message)
        assert not manager.return_value.crawl.called

    def test_render_POST_invalid_options(self, t_req, resource):
        t_req.content.getvalue.return_value = json.dumps(
            {"spider_name": "tests", "request": {"foo": "bar"}},
        )
        resource.validate_options = Mock()
        with patch("scrapyrt.core.CrawlManager", spec=True), pytest.raises(Error) as e:
            resource.render_POST(t_req)
        assert e.value.status == b"400"
        assert e.value.message
        msg = b"'foo' is not a valid argument"
        assert re.search(msg, e.value.message)

    @pytest.mark.parametrize(
        ("scrapy_args", "api_args", "has_error"),
        (({"url": "aa"}, {}, False), ({}, {}, True)),
    )
    def test_validate_options(self, resource, scrapy_args, api_args, has_error):
        if has_error:
            with pytest.raises(Error) as e:
                resource.validate_options(scrapy_args, api_args)
            assert e.value.status == b"400"
            assert e.value.message
            assert re.search(b"'url' is required", e.value.message)
        else:
            result = resource.validate_options(scrapy_args, api_args)
            assert result is None

    def test_prepare_response(self, resource):
        result = {"items": [1, 2], "stats": [99], "spider_name": "test"}
        prepared_res = resource.prepare_response(result, {})
        expected = [
            ("status", "ok"),
            ("items", [1, 2]),
            ("items_dropped", []),
            ("stats", [99]),
            ("spider_name", "test"),
        ]
        for key, value in expected:
            assert prepared_res[key] == value

    def test_prepare_response_errors(self, resource):
        result = {
            "items": [1, 2],
            "stats": [99],
            "spider_name": "test",
            "errors": ["foo"],
        }
        actual = resource.prepare_response(result, {})
        expected = {
            "status": "ok",
            "items": [1, 2],
            "items_dropped": [],
            "stats": [99],
            "spider_name": "test",
            "errors": ["foo"],
        }
        assert expected == actual

    def test_prepare_response_user_error_raised(self, resource):
        result: dict[str, Any] = {"items": [1, 2], "stats": [99], "spider_name": "test"}
        result["user_error"] = Exception("my exception")
        with pytest.raises(Exception) as e_info:  # noqa: PT011
            resource.prepare_response(result, {})
        assert str(e_info.value) == "my exception"


class TestCrawlResourceGetRequiredArgument(unittest.TestCase):
    def setUp(self):
        self.resource = CrawlResource()
        self.url = "http://localhost:1234"
        self.data = {"url": self.url}

    def test_get_argument(self):
        assert self.resource.get_required_argument(self.data, "url") == self.url

    def test_raise_error(self):
        with pytest.raises(Error) as exception:
            self.resource.get_required_argument(self.data, "key")
        assert exception.value.status == b"400"

    def test_empty_argument(self):
        self.data["url"] = ""
        with pytest.raises(Error) as exception:
            self.resource.get_required_argument(self.data, "url")
        assert exception.value.status == b"400"


def perform_get(url, api_params, spider_data=None):
    spider_data = spider_data or {}
    api_params.update(spider_data)
    return requests.get(url, params=api_params, timeout=30)


def perform_post(url, api_params, spider_data=None):
    spider_data = spider_data or {}
    post_data = {"request": spider_data}
    post_data.update(api_params)
    return requests.post(url, json=post_data, timeout=30)


class TestCrawlResourceIntegration:
    @pytest.mark.parametrize("method", (perform_get, perform_post))
    def test_no_parameters(self, method, server):
        res = method(server.url("crawl.json"), {}, {})
        assert res.status_code == 400
        res_json = res.json()
        expected_result = {"status": "error", "code": 400}
        for key, value in expected_result.items():
            assert res_json.get(key) == value
        if res.request.method == "GET":
            assert "url" in res_json["message"]
        else:
            assert "request" in res_json["message"]

    @pytest.mark.parametrize("method", (perform_get, perform_post))
    def test_no_url_no_start_requests(self, server, method):
        res = method(server.url("crawl.json"), {"spider_name": "test"}, {})
        assert res.status_code == 400
        expected_result = {"status": "error", "code": 400}
        res_json = res.json()
        for key, value in expected_result.items():
            assert res_json[key] == value
        if res.request.method == "GET":
            assert "url" in res_json["message"]
        else:
            assert "request" in res_json["message"]

    @pytest.mark.parametrize("method", (perform_get, perform_post))
    def test_no_url_but_spider_start_present(self, server, method):
        res = method(
            server.url("crawl.json"),
            {"spider_name": "test_with_sr", "spider_start": True},
            {},
        )
        assert res.status_code == 200
        result = res.json()
        assert result.get("status") == "ok"
        assert result.get("stats") is not None
        assert len(result.get("items", [])) == 2
        items = result["items"]
        assert len(items) == 2
        for item in items:
            name = item["name"][0]
            if name == "Page 1":
                assert "page1" in item["referer"]
            elif name == "Page 2":
                assert "page2" in item["referer"]

        spider_errors = result.get("errors", [])
        assert len(spider_errors) == 0
        assert result["stats"].get("downloader/request_count") == 2

    def test_no_request_in_POST_handler(self, server):
        """Test for POST handler checking if everything works fine
        if there is no 'request' argument at all.
        """
        post_data = {"no_request": {}, "spider_name": "test_with_sr"}
        post_data.update(post_data)
        res = requests.post(server.url("crawl.json"), json=post_data, timeout=30)
        assert res.status_code == 400
        data = res.json()
        msg = "Missing required parameter: 'request'"
        assert data["message"] == msg
        assert data["status"] == "error"
        assert data.get("items") is None

    @pytest.mark.parametrize("method", (perform_get, perform_post))
    def test_no_spider_name(self, server, method):
        res = method(
            server.url("crawl.json"),
            {},
            {"url": server.site.url("page1.html")},
        )
        assert res.status_code == 400
        res_json = res.json()
        expected_result = {"status": "error", "code": 400}
        for key, value in expected_result.items():
            assert res_json[key] == value
        assert "spider_name" in res_json["message"]

    def test_invalid_scrapy_request_detected_in_api(self, server):
        res = perform_post(
            server.url("crawl.json"),
            {"spider_name": "test"},
            {"url": server.site.url("page1.html"), "not_an_argument": False},
        )
        assert res.status_code == 400
        res_json = res.json()
        expected_result = {"status": "error", "code": 400}
        for k, v in expected_result.items():
            assert res_json[k] == v
        assert "'not_an_argument' is not a valid arg" in res_json["message"]

    @pytest.mark.parametrize("method", (perform_get, perform_post))
    def test_invalid_scrapy_request_detected_by_scrapy(self, server, method):
        res = method(
            server.url("crawl.json"),
            {"spider_name": "test"},
            {"url": "no_rules"},
        )
        assert res.status_code == 400
        res_json = res.json()
        assert res_json["status"] == "error"
        assert res_json["code"] == 400
        assert "Error while creating Scrapy Request" in res_json["message"]

    @pytest.mark.parametrize("method", (perform_get, perform_post))
    def test_crawl(self, server, method):
        url = server.url("crawl.json")
        res = method(
            url,
            {"spider_name": "test"},
            {"url": server.site.url("page1.html")},
        )
        expected_items = [
            {
                "name": ["Page 1"],
            },
        ]
        res_json = res.json()
        assert res_json["status"] == "ok"
        assert res_json["items_dropped"] == []
        assert res_json["items"]
        assert len(res_json["items"]) == len(expected_items)
        assert res_json["items"] == expected_items

    def test_invalid_json_in_post(self, server):
        res = requests.post(server.url("crawl.json"), data="ads", timeout=30)
        assert res.status_code == 400
        res_json = res.json()
        expected_result = {"status": "error", "code": 400}
        for k, v in expected_result.items():
            assert res_json[k] == v
        msg = "Invalid JSON in POST body"
        assert msg in res_json["message"]

    @pytest.mark.parametrize("method", (perform_get, perform_post))
    def test_passing_errback(self, server, method):
        url = server.url("crawl.json")
        res = method(
            url,
            {"spider_name": "test"},
            {"url": server.site.url("err/503"), "errback": "some_errback"},
        )

        res_json = res.json()
        assert res_json.get("stats").get("log_count/ERROR") == 2
        assert res_json["status"] == "ok"
        logs_path = Path(server.cwd) / "logs" / "test"
        logs_file = next(iter(logs_path.iterdir()))
        with (logs_path / logs_file).open() as f:
            log_file_contents = f.read()

        msg = "ERROR: Logging some error"
        assert re.search(msg, log_file_contents)

    @pytest.mark.parametrize("method", (perform_get, perform_post))
    def test_bytes_in_item(self, server, method):
        url = server.url("crawl.json")
        res = method(
            url,
            {"spider_name": "test"},
            {"url": server.site.url("page1.html"), "callback": "return_bytes"},
        )
        assert res.status_code == 200
        assert res.json()["items"] == [{"name": "Some bytes here"}]

    def test_crawl_with_argument_get(self, server):
        url = server.url("crawl.json")
        postcode = "43-300"
        argument = json.dumps({"postcode": postcode})
        argument = quote(argument)
        res = perform_get(
            url,
            {"spider_name": "test"},
            {
                "url": server.site.url("page1.html"),
                "crawl_args": argument,
                "callback": "return_argument",
            },
        )
        expected_items = [
            {
                "name": postcode,
            },
        ]
        res_json = res.json()
        assert res_json["status"] == "ok"
        assert res_json["items_dropped"] == []
        assert res_json["items"]
        assert len(res_json["items"]) == len(expected_items)
        assert res_json["items"] == expected_items

    def test_crawl_with_argument_post(self, server):
        url = server.url("crawl.json")
        postcode = "43-300"
        argument = {"postcode": postcode}
        res = perform_post(
            url,
            {"spider_name": "test", "crawl_args": argument},
            {
                "url": server.site.url("page1.html"),
                "callback": "return_argument",
            },
        )
        expected_items = [
            {
                "name": postcode,
            },
        ]
        res_json = res.json()
        assert res.status_code == 200
        assert res_json["status"] == "ok"
        assert not res_json.get("errors")
        assert res_json["items_dropped"] == []
        assert res_json["items"]
        assert len(res_json["items"]) == len(expected_items)
        assert res_json["items"] == expected_items

    def test_crawl_with_argument_invalid_json(self, server):
        url = server.url("crawl.json")
        argument = '"this is not valid json'
        argument = quote(argument)
        res = perform_get(
            url,
            {"spider_name": "test"},
            {
                "url": server.site.url("page1.html"),
                "crawl_args": argument,
                "callback": "return_argument",
            },
        )
        assert res.status_code == 400
        res_json = res.json()
        assert res_json["status"] == "error"
        assert res_json.get("items") is None
        assert res_json["code"] == 400
        assert re.search(" must be valid url encoded JSON", res_json["message"])

    def test_crawl_with_argument_invalid_name(self, server):
        url = server.url("crawl.json")
        argument = quote(json.dumps({"parse": "string"}))
        res = perform_get(
            url,
            {"spider_name": "test"},
            {
                "url": server.site.url("page1.html"),
                "crawl_args": argument,
            },
        )

        def check_res(res):
            res_json = res.json()
            assert res.status_code == 400
            assert res_json["status"] == "error"
            assert res_json.get("items") is None
            assert res_json["code"] == 400

            msg = "Crawl argument cannot override spider method"
            assert re.search(msg, res_json["message"])

        check_res(res)

        res = perform_post(
            url,
            {"spider_name": "test", "crawl_args": argument},
            {
                "url": server.site.url("page1.html"),
                "callback": "return_argument",
            },
        )

        check_res(res)

    def test_crawl_with_argument_attribute_collision(self, server):
        """If there is attribute collision and some argument to spider
        passed via API, and this argument collides with spider attribute,
        argument from request overrides spider attribute.
        """
        url = server.url("crawl.json")
        argument = quote(json.dumps({"some_attribute": "string"}))
        res = perform_get(
            url,
            {"spider_name": "test"},
            {
                "url": server.site.url("page1.html"),
                "crawl_args": argument,
            },
        )

        def check_res(res):
            res_json = res.json()
            assert res_json["status"] == "ok"
            assert res.status_code == 200
            assert res_json["items"]
            assert len(res_json["items"]) == 1

        check_res(res)
