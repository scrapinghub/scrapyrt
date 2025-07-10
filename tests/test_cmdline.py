import subprocess
import sys
import tempfile
from os import chdir
from pathlib import Path
from typing import NamedTuple
from unittest.mock import patch

import port_for
import pytest
from scrapy.utils.conf import closest_scrapy_cfg
from twisted.python.components import Componentized

from scrapyrt.cmdline import execute, find_scrapy_project, get_application
from scrapyrt.conf import app_settings

from .utils import ASYNCIO_REACTOR_IS_DEFAULT, generate_project, get_testenv


class FakeArgs(NamedTuple):
    port: int
    ip: str
    set: list
    project: str
    settings: str


def make_fake_args() -> FakeArgs:
    return FakeArgs(9080, "0.0.0.0", [], "default", "")


@pytest.fixture
def workdir():
    tmp_dir = Path(tempfile.mkdtemp())
    workdir = tmp_dir / "testproject"
    generate_project(workdir)
    chdir(workdir)
    return workdir


class TestCmdLine:
    def test_find_scrapy_project(self, workdir):
        settings = find_scrapy_project("default")
        assert settings == "testproject.settings"
        assert str(workdir) in sys.path

    def test_find_scrapy_project_invalid_conf(self, workdir):
        config = Path(closest_scrapy_cfg())
        with config.open("wb") as f:
            f.write(b"[other_section]")
        with pytest.raises(RuntimeError) as err:
            find_scrapy_project("default")
        assert str(err.value) == "No section: 'settings'"

    def test_get_application(self):
        app = get_application(make_fake_args())
        assert isinstance(app, Componentized)

    @patch("scrapyrt.cmdline.run_application")
    @patch("scrapyrt.cmdline.parse_arguments", new_callable=lambda: make_fake_args)
    def test_execute(self, mock_pa, mock_run_app, workdir):
        execute()
        expected_first_param = (
            "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
            if ASYNCIO_REACTOR_IS_DEFAULT
            else None
        )
        mock_run_app.assert_called_once_with(
            expected_first_param, mock_pa(), app_settings
        )

    @pytest.mark.parametrize(
        ("reactor", "expected"),
        [
            (
                "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
                "AsyncioSelectorReactor",
            ),
            (
                None,
                "AsyncioSelectorReactor"
                if ASYNCIO_REACTOR_IS_DEFAULT
                else "EPollReactor",
            ),
            ("twisted.internet.epollreactor.EPollReactor", "EPollReactor"),
        ],
    )
    def test_reactor_launched(self, reactor, expected):
        port = port_for.select_random()
        tmp_dir = Path(tempfile.mkdtemp())
        cwd = tmp_dir / "testproject"
        generate_project(cwd)
        cmd = [
            sys.executable,
            "-m",
            "scrapyrt.cmdline",
            "-p",
            str(port),
        ]
        if reactor is not None:
            cmd.extend(["-s", f"TWISTED_REACTOR={reactor}"])

        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=get_testenv(),
        )
        try:
            _, logs = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.terminate()
            _, logs = process.communicate()
        assert f"Running with reactor: {expected}" in logs.decode()
