# -*- coding: utf-8 -*-
from twisted.trial import unittest
from twisted.web.error import Error
import requests

from scrapyrt.resources import CrawlResource

from .servers import ScrapyrtTestServer, MockServer


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


class TestCrawlResourceIntegration(unittest.TestCase):

    def setUp(self):
        self.server = ScrapyrtTestServer()
        self.server.start()
        self.crawl_url = self.server.url('crawl.json')
        self.site = MockServer()
        self.site.start()
        self.site_url = self.site.url('page1.html')
        self.spider_name = 'test'

    def tearDown(self):
        if not self._passed:
            print self.server._non_block_read(self.server.proc.stderr)
        self.server.stop()
        self.site.stop()

    def get_and_post(self, url, api_params, spider_data):
        get_params = api_params.copy()
        get_params.update(spider_data)
        res_get = requests.get(
            url, params=get_params
        )
        post_data = {
            "request": spider_data
        }
        post_data.update(api_params)
        res_post = requests.post(
            url,
            json=post_data
        )
        return res_get, res_post

    def test_no_parameters(self):
        r1, r2 = self.get_and_post(self.crawl_url, {}, {})
        for res in (r1, r2):
            assert res.status_code == 400
            res_json = res.json()
            expected_result = {u'status': u'error',  u'code': 400}
            self.assertDictContainsSubset(expected_result, res_json)
            if res.request.method == "GET":
                assert 'url' in res_json['message']
            else:
                assert "request" in res_json["message"]

    def test_no_url_no_start_requests(self):
        r1, r2 = self.get_and_post(self.crawl_url, {'spider_name': self.spider_name}, {})
        for res in (r1, r2):
            assert res.status_code == 400
            expected_result = {
                u'status': u'error',
                u'code': 400
            }
            res_json = res.json()
            self.assertDictContainsSubset(expected_result, res_json)
            if res.request.method == "GET":
                assert 'url' in res_json['message']
            else:
                assert "request" in res_json["message"]

    def test_no_url_but_start_requests_present(self):
        r1, r2 = self.get_and_post(self.crawl_url, {
            'spider_name': self.spider_name,
            "start_requests": True
        }, {})
        for res in (r1, r2):
            assert res.status_code == 200
            assert res.json().get("status") == "ok"

    def test_no_spider_name(self):
        res = requests.get(
            self.crawl_url,
            params={
                'url': self.site_url,
            }
        )
        assert res.status_code == 400
        res_json = res.json()
        expected_result = {
            u'status': u'error',
            u'code': 400
        }
        self.assertDictContainsSubset(expected_result, res_json)
        assert 'spider_name' in res_json['message']

    def test_invalid_scrapy_request_detected_in_api(self):
        res = requests.post(
            self.crawl_url,
            json={
                "request": {
                    'url': self.site_url,
                    "not_an_argument": False
                },
                "spider_name": self.spider_name,
            }
        )
        assert res.status_code == 400
        res_json = res.json()
        expected_result = {
            u'status': u'error',
            u'code': 400
        }
        self.assertDictContainsSubset(expected_result, res_json)
        assert "'not_an_argument' is not a valid argument" in res_json['message']

    def test_invalid_scrapy_request_detected_by_scrapy(self):
        r1, r2 = self.get_and_post(
            self.crawl_url,
            {"spider_name": self.spider_name},
            {'url': "no_rules"}
        )
        for res in (r1, r2):
            assert res.status_code == 400
            res_json = res.json()
            expected_result = {
                u'status': u'error',
                u'code': 400
            }
            self.assertDictContainsSubset(expected_result, res_json)
            assert "Error while creating Scrapy Request" in res_json['message']

    def test_crawl(self):
        res = requests.get(
            self.crawl_url,
            params={
                'url': self.site_url,
                'spider_name': self.spider_name
            }
        )

        expected_result = {
            u'status': u'ok',
            u'items_dropped': []
        }
        expected_items = [{
            u'name': ['Page 1'],
        }]
        res_json = res.json()
        self.assertDictContainsSubset(expected_result, res_json)
        assert res_json['items']
        assert len(res_json['items']) == len(expected_items)
        for exp_item, res_item in zip(expected_items, res_json['items']):
            self.assertDictContainsSubset(exp_item, res_item)
