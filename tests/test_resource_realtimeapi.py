import os
from copy import deepcopy
from unittest.mock import patch

from twisted.trial import unittest

from scrapyrt.conf import app_settings
from scrapyrt.resources import CrawlResource, RealtimeApi, ServiceResource


class SampleResource(ServiceResource):
    isLeaf = True
    allowedMethods = [b"GET", b"POST"]

    def render_GET(self, request, **kwargs):
        return {"status": "ok"}


class TestRealtimeApi(unittest.TestCase):
    @staticmethod
    def _get_class_path(clsname):
        module_name, _, _ = os.path.basename(__file__).rpartition(".")
        return f"{__package__}.{module_name}.{clsname}"

    def test_realtimeapi_with_default_settings(self):
        expected_entities = {b"crawl.json": CrawlResource}
        service_root = RealtimeApi()
        self._check_entities(service_root, expected_entities)

    # XXX: one inconvenience of singleton settings - complexities during tests,
    # e.g. settings are mutable, when you change them in one test -
    # changes will be kept unless you cleanup those changes or use mock.
    @patch("scrapyrt.resources.app_settings", deepcopy(app_settings))
    def test_realtimeapi_with_custom_settings(self):
        from scrapyrt.resources import app_settings

        app_settings.RESOURCES[b"test.json"] = self._get_class_path("SampleResource")
        expected_entities = {b"crawl.json": CrawlResource, b"test.json": SampleResource}
        service_root = RealtimeApi()
        self._check_entities(service_root, expected_entities)

    def _check_entities(self, service_root, expected_entities):
        self.assertFalse(service_root.isLeaf)
        entities = service_root.listEntities()
        self.assertEqual(len(entities), len(expected_entities))
        for name, entity in entities:
            self.assertIn(name, expected_entities)
            self.assertIsInstance(entity, expected_entities[name])
