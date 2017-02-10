# -*- coding: utf-8 -*-
from copy import deepcopy
import os

from mock import patch
from twisted.trial import unittest

from scrapyrt.conf import settings
from scrapyrt.resources import RealtimeApi, ServiceResource, CrawlResource


class TestResource(ServiceResource):
    isLeaf = True
    allowedMethods = ['GET', 'POST']

    def render_GET(self, request, **kwargs):
        return {'status': 'ok'}


class TestRealtimeApi(unittest.TestCase):

    @staticmethod
    def _get_class_path(clsname):
        module_name, _, _ = os.path.basename(__file__).rpartition('.')
        return '{}.{}.{}'.format(__package__, module_name, clsname)

    def test_realtimeapi_with_default_settings(self):
        expected_entities = {b'crawl.json': CrawlResource}
        service_root = RealtimeApi()
        self._check_entities(service_root, expected_entities)

    # XXX: one inconvenience of singleton settings - complexities during tests,
    # e.g. settings are mutable, when you change them in one test -
    # changes will be kept unless you cleanup those changes or use mock.
    @patch('scrapyrt.resources.settings', deepcopy(settings))
    def test_realtimeapi_with_custom_settings(self):
        from scrapyrt.resources import settings
        settings.RESOURCES[b'test.json'] = self._get_class_path('TestResource')
        expected_entities = {
            b'crawl.json': CrawlResource,
            b'test.json': TestResource
        }
        service_root = RealtimeApi()
        self._check_entities(service_root, expected_entities)

    def _check_entities(self, service_root, expected_entities):
        self.assertFalse(service_root.isLeaf)
        entities = service_root.listEntities()
        self.assertEqual(len(entities), len(expected_entities))
        for name, entity in entities:
            self.assertIn(name, expected_entities)
            self.assertIsInstance(entity, expected_entities[name])
