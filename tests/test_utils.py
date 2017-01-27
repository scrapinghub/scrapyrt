import re

import pytest

from scrapyrt.utils import extract_scrapy_request_args


class TestUtils(object):
    def test_get_scrapy_request_args(self):
        args = {
            "url": "http://foo.com",
            "callback": "parse",
            "noise": True
        }

        result = extract_scrapy_request_args(args)

        assert result["url"] == "http://foo.com"
        assert result["callback"] == "parse"
        assert "noise" not in result

    def test_get_scrapy_request_args_error(self):
        args = {
            "url": "http://foo.com",
            "callback": "parse",
            "noise": True
        }

        with pytest.raises(ValueError) as e:
            extract_scrapy_request_args(args, raise_error=True)

        expected_msg =u"'noise' is not a valid argument for scrapy.Request"
        assert re.search(expected_msg, str(e.value))

