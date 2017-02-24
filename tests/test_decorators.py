from mock import patch

from scrapyrt.decorators import deprecated
from scrapyrt.exceptions import ScrapyrtDeprecationWarning


class TestDecorators(object):
    def test_deprecated(self):
        @deprecated
        def test_func(*args, **kwargs):
            return (args, kwargs)

        with patch('warnings.warn') as w:
            args, kwargs = test_func('foo', 'bar', keyword='blue')

        msg = 'Call to deprecated function test_func.'
        w.assert_called_once_with(msg,
                                  category=ScrapyrtDeprecationWarning,
                                  stacklevel=2)
        assert args == ('foo', 'bar')
        assert kwargs['keyword'] == 'blue'
