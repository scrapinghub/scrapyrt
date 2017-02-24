# -*- coding: utf-8 -*-
import json

import pytest
import re
from mock import MagicMock, patch, Mock
from twisted.trial import unittest
from twisted.web.error import Error
import requests
from twisted.web.server import Request

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


@pytest.fixture()
def t_req():
    return MagicMock(spec=Request)


@pytest.fixture()
def resource():
    return CrawlResource()


class TestCrawlResource(object):

    def test_is_leaf(self):
        assert CrawlResource.isLeaf

    def test_render_GET(self, t_req, resource):
        t_req.args = {
            b'url': [b'http://foo'],
            b'spider_name': [b'test']
        }
        resource.validate_options = Mock()

        with patch('scrapyrt.core.CrawlManager', spec=True) as manager:
            instance = manager.return_value
            resource.render_GET(t_req)
        scrapy_params = {'url': 'http://foo'}
        api_params = {'spider_name': 'test', 'url': 'http://foo'}
        resource.validate_options.assert_called_once_with(
            scrapy_params, api_params
        )
        assert instance.crawl.called

    def test_render_POST(self, t_req, resource):
        t_req.content.getvalue.return_value = json.dumps({
                'spider_name': 'test',
                'request': {
                    'url': 'http://foo.com'
                }
        })
        resource.validate_options = Mock()
        with patch('scrapyrt.core.CrawlManager', spec=True) as manager:
            instance = manager.return_value
            resource.render_POST(t_req)

        scrapy_params = {'url': 'http://foo.com'}
        api_params = {
            'request': {'url': 'http://foo.com'},
            'spider_name': 'test'
        }
        assert instance.crawl.called
        resource.validate_options.assert_called_once_with(
            scrapy_params, api_params
        )

    def test_render_POST_invalid_json(self, t_req, resource):
        t_req.content.getvalue.return_value = b'{{{{{'
        with patch('scrapyrt.core.CrawlManager', spec=True) as manager:
            with pytest.raises(Error) as e:
                resource.render_POST(t_req)
        assert e.value.status == '400'
        assert re.search('Invalid JSON in POST', e.value.message)
        assert not manager.return_value.crawl.called

    def test_render_POST_invalid_options(self, t_req, resource):
        t_req.content.getvalue.return_value = json.dumps({
            'spider_name': 'tests',
            'request': {
                'foo': 'bar'
            }
        })
        resource.validate_options = Mock()
        with patch('scrapyrt.core.CrawlManager', spec=True):
            with pytest.raises(Error) as e:
                resource.render_POST(t_req)
        assert e.value.status == '400'
        msg = "'foo' is not a valid argument"
        assert re.search(msg, e.value.message)

    @pytest.mark.parametrize('scrapy_args,api_args,has_error', [
        ({'url': 'aa'}, {}, False),
        ({}, {}, True)
    ])
    def test_validate_options(self, resource,
                              scrapy_args, api_args, has_error):
        if has_error:
            with pytest.raises(Error) as e:
                resource.validate_options(scrapy_args, api_args)
            assert e.value.status == '400'
            assert re.search("\'url\' is required", e.value.message)
        else:
            result = resource.validate_options(scrapy_args, api_args)
            assert result is None

    def test_prepare_response(self, resource):
        result = {
            'items': [1, 2],
            'stats': [99],
            'spider_name': 'test'
        }
        prepared_res = resource.prepare_response(result)
        expected = [
            ('status', 'ok'),
            ('items', [1, 2]),
            ('items_dropped', []),
            ('stats', [99]),
            ('spider_name', 'test')
        ]
        for key, value in expected:
            assert prepared_res[key] == value


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

    def test_no_request_but_start_requests_present(self, server):
        """Test for POST handler checking if everything works fine
        if there is no 'request' argument, but 'start_requests' are
        present. Not checked above because of the way default test fixtures
        are written.
        """
        post_data = {
            "no_request": {},
            "start_requests": True,
            "spider_name": "test_with_sr"
        }
        post_data.update(post_data)
        res = requests.post(server.url("crawl.json"),
                            json=post_data)
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 2
        assert data.get("errors") is None

    def test_no_request_in_POST_handler(self, server):
        """Test for POST handler checking if everything works fine
        if there is no 'request' argument at all.
        """
        post_data = {
            "no_request": {},
            "spider_name": "test_with_sr"
        }
        post_data.update(post_data)
        res = requests.post(server.url("crawl.json"),
                            json=post_data)
        assert res.status_code == 400
        data = res.json()
        msg = u"Missing required parameter: 'request'"
        assert data["message"] == msg
        assert data["status"] == "error"
        assert data.get("items") is None

    @pytest.mark.parametrize("method", [
        perform_get, perform_post
    ])
    def test_url_and_start_requests_present(self, server, method):
        spider_data = {
            "url": server.target_site.url("page3.html")
        }
        api_params = {
            "spider_name": "test_with_sr",
            "start_requests": True,
        }
        res = method(server.url("crawl.json"), api_params,
                     spider_data)
        assert res.status_code == 200
        output = res.json()
        assert len(output.get("errors", [])) == 0
        items = output.get("items", [])
        assert len(items) == 3

        for item in items:
            name = item["name"][0]
            if name == "Page 1":
                assert "page1" in item["referer"]
            elif name == "Page 2":
                assert "page2" in item["referer"]
            elif name == "Page 3":
                assert item.get("referer") is None

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

    def test_invalid_json_in_post(self, server):
        res = requests.post(server.url("crawl.json"), data="ads")
        assert res.status_code == 400
        res_json = res.json()
        expected_result = {
            u'status': u'error',
            u'code': 400
        }
        for k, v in expected_result.items():
            assert res_json[k] == v
        msg = "Invalid JSON in POST body"
        assert msg in res_json['message']
