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

    def test_no_parameters(self):
        res = requests.get(self.crawl_url)
        assert res.status_code == 400
        res_json = res.json()
        expected_result = {u'status': u'error',  u'code': 400}
        self.assertDictContainsSubset(expected_result, res_json)
        assert 'url' in res_json['message']

    def test_no_url(self):
        res = requests.get(
            self.crawl_url,
            params={
                'spider_name': self.spider_name
            }
        )
        assert res.status_code == 400
        expected_result = {
            u'status': u'error',
            u'code': 400
        }
        res_json = res.json()
        self.assertDictContainsSubset(expected_result, res_json)
        assert 'url' in res_json['message']

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
