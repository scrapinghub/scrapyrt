import requests
from twisted.trial import unittest

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
            assert self.server.proc is not None
            print(self.server._non_block_read(self.server.proc.stderr))
        self.server.stop()
        self.site.stop()

    def test_root(self):
        res = requests.get(self.root_url, timeout=30)
        assert res.status_code == 404
        assert "No Such Resource" in res.text
