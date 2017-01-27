# -*- coding: utf-8 -*-
from twisted.trial import unittest
import requests

from .servers import MockServer, ScrapyrtTestServer


class TestRootResourceIntegration(unittest.TestCase):

    def setUp(self):
        self.site = MockServer()
        self.site.start()
        self.server = ScrapyrtTestServer(site=self.site)
        self.server.start()
        self.root_url = self.server.url()

    def tearDown(self):
        if not self._passed:
            print(self.server._non_block_read(self.server.proc.stderr))
        self.server.stop()
        self.site.stop()

    def test_root(self):
        res = requests.get(self.root_url)
        assert res.status_code == 404
        assert 'No Such Resource' in res.text
