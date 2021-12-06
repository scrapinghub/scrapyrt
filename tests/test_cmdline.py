import os
import subprocess
import sys
import tempfile
from collections import namedtuple
from os import path, chdir
from mock import patch

import port_for
import pytest
from scrapy.utils.conf import closest_scrapy_cfg
from twisted.python.components import Componentized

from scrapyrt.cmdline import execute, find_scrapy_project, get_application
from scrapyrt.conf import app_settings
from tests.utils import generate_project, get_testenv


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

    @patch('scrapyrt.cmdline.run_application')
    @patch('scrapyrt.cmdline.parse_arguments',
           new_callable=lambda: make_fake_args)
    def test_execute(self, mock_pa, mock_run_app, workdir):
        execute()
        mock_run_app.assert_called_once_with(None, mock_pa(), app_settings)

    @pytest.mark.parametrize('reactor,expected', [
        ("twisted.internet.asyncioreactor.AsyncioSelectorReactor",
         "AsyncioSelectorReactor"),
        (None, 'EPollReactor')
    ])
    def test_reactor_launched(self, reactor, expected):
        port = port_for.select_random()

        tmp_dir = tempfile.mkdtemp()
        cwd = os.path.join(tmp_dir, 'testproject')
        generate_project(cwd)
        cmd = [
            sys.executable, '-m', 'scrapyrt.cmdline', '-p', str(port),
        ]
        if reactor is not None:
            cmd.extend(['-s', f'TWISTED_REACTOR={reactor}'])

        process = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   env=get_testenv())
        try:
            _, logs = process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            _, logs = process.communicate()
        assert f"Running with reactor: {expected}" in logs.decode()
