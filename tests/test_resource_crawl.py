# -*- coding: utf-8 -*-
import pytest
from twisted.trial import unittest
from twisted.web.error import Error
import requests

from scrapyrt.resources import CrawlResource

from .servers import ScrapyrtTestServer, MockServer


@pytest.fixture()
def server(request):
    target_site = MockServer()
    target_site.start()
    server = ScrapyrtTestServer(site=target_site)

    def close():
        server.stop()
        target_site.stop()

    request.addfinalizer(close)
    server.target_site = target_site
    server.start()
    return server


class TestCrawlResource(unittest.TestCase):

    def test_is_leaf(self):
        self.assertTrue(CrawlResource.isLeaf)


class TestCrawlResourceGetRequiredArgument(unittest.TestCase):

    def setUp(self):
        self.resource = CrawlResource()
        self.url = 'http://localhost:1234'
        self.data = {'url': self.url}

    def test_get_argument(self):
        self.assertEqual(
            self.resource.get_required_argument(self.data, 'url'), self.url)

    def test_raise_error(self):
        exception = self.assertRaises(
            Error, self.resource.get_required_argument, self.data, 'key')
        self.assertEqual(exception.status, '400')

    def test_empty_argument(self):
        self.data['url'] = ''
        exception = self.assertRaises(
            Error, self.resource.get_required_argument, self.data, 'url')
        self.assertEqual(exception.status, '400')


def perform_get(url, api_params, spider_data):
    api_params.update(spider_data)
    return requests.get(url, params=api_params)


def perform_post(url, api_params, spider_data):
    post_data = {"request": spider_data}
    post_data.update(api_params)
    return requests.post(url, json=post_data)


class TestCrawlResourceIntegration(object):
    @pytest.mark.parametrize("method", [
        perform_get, perform_post
    ])
    def test_no_parameters(self, server, method):
        res = method(server.url('crawl.json'), {}, {})
        assert res.status_code == 400
        res_json = res.json()
        expected_result = {u'status': u'error',  u'code': 400}
        for key, value in expected_result.items():
            assert res_json.get(key) == value
        if res.request.method == "GET":
            assert 'url' in res_json['message']
        else:
            assert "request" in res_json["message"]

    @pytest.mark.parametrize("method", [
        perform_get, perform_post
    ])
    def test_no_url_no_start_requests(self, server, method):
        res = method(server.url('crawl.json'), {'spider_name': 'test'},
                     {})
        assert res.status_code == 400
        expected_result = {
            u'status': u'error',
            u'code': 400
        }
        res_json = res.json()
        for key, value in expected_result.items():
            assert res_json[key] == value
        if res.request.method == "GET":
            assert 'url' in res_json['message']
        else:
            assert "request" in res_json["message"]

    @pytest.mark.parametrize("method", [
        perform_get, perform_post
    ])
    def test_no_url_but_start_requests_present(self, server, method):
        res = method(server.url("crawl.json"), {
            'spider_name': "test_with_sr",
            "start_requests": True
        }, {})
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

    @pytest.mark.parametrize("method", [
        perform_get, perform_post
    ])
    def test_no_spider_name(self, server, method):
        res = method(server.url("crawl.json"),
                     {},
                     {"url": server.target_site.url("page1.html")})
        assert res.status_code == 400
        res_json = res.json()
        expected_result = {
            u'status': u'error',
            u'code': 400
        }
        for key, value in expected_result.items():
            assert res_json[key] == value
        assert 'spider_name' in res_json['message']

    def test_invalid_scrapy_request_detected_in_api(self, server):
        res = perform_post(server.url("crawl.json"),
                           {"spider_name": "test"},
                           {'url': server.target_site.url("page1.html"),
                            "not_an_argument": False})
        assert res.status_code == 400
        res_json = res.json()
        expected_result = {
            u'status': u'error',
            u'code': 400
        }
        for k, v in expected_result.items():
            assert res_json[k] == v
        assert "'not_an_argument' is not a valid arg" in res_json['message']

    @pytest.mark.parametrize("method", [
        perform_get, perform_post
    ])
    def test_invalid_scrapy_request_detected_by_scrapy(self, server, method):
        res = method(
            server.url("crawl.json"),
            {"spider_name": "test"},
            {'url': "no_rules"}
        )
        assert res.status_code == 400
        res_json = res.json()
        assert res_json["status"] == "error"
        assert res_json["code"] == 400
        assert "Error while creating Scrapy Request" in res_json['message']

    @pytest.mark.parametrize("method", [
        perform_get, perform_post
    ])
    def test_crawl(self, server, method):
        url = server.url("crawl.json")
        res = method(url,
                     {"spider_name": "test"},
                     {"url": server.target_site.url("page1.html")})
        expected_items = [{
            u'name': ['Page 1'],
        }]
        res_json = res.json()
        assert res_json["status"] == "ok"
        assert res_json["items_dropped"] == []
        assert res_json['items']
        assert len(res_json['items']) == len(expected_items)
        assert res_json["items"] == expected_items
