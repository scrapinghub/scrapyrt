import pytest
import sys
import tempfile
from collections import namedtuple
from os import path, chdir
from scrapy.utils.conf import closest_scrapy_cfg
from twisted.python.components import Componentized

from scrapyrt.cmdline import find_scrapy_project, get_application
from tests.utils import generate_project


def make_fake_args():
    fake_args = namedtuple('arguments', [
        'port',
        'ip',
        'set',
        'project',
        'settings'
    ])
    return fake_args(
        9080,
        '0.0.0.0',
        [],
        'default',
        ''
    )


@pytest.fixture
def workdir():
    tmp_dir = tempfile.mkdtemp()
    workdir = path.join(tmp_dir, 'testproject')
    generate_project(workdir)
    chdir(workdir)
    return workdir


class TestCmdLine(object):
    def test_find_scrapy_project(self, workdir):
        settings = find_scrapy_project('default')
        assert 'testproject.settings' == settings
        assert workdir in sys.path

    def test_find_scrapy_project_invalid_conf(self, workdir):
        config = closest_scrapy_cfg()
        with open(config, 'wb') as f:
            f.write(b'[other_section]')
        with pytest.raises(RuntimeError) as err:
            find_scrapy_project('default')
        assert str(err.value) == "No section: 'settings'"

    def test_get_application(self):
        app = get_application(make_fake_args())
        assert isinstance(app, Componentized)
