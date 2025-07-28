import subprocess
import sys
import tempfile
from contextlib import contextmanager
from os import chdir
from pathlib import Path
from tempfile import TemporaryDirectory
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


@contextmanager
def ProjectDirectory():
    with TemporaryDirectory() as tmp_dir:
        directory = Path(tmp_dir) / "testproject"
        generate_project(directory)
        yield directory


def run(directory, args=None, timeout=2) -> bytes:
    args = args or []
    port = port_for.select_random()
    cmd = [
        sys.executable,
        "-m",
        "scrapyrt.cmdline",
        "-p",
        str(port),
        *args,
    ]
    process = subprocess.Popen(
        cmd,
        cwd=directory,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=get_testenv(),
    )
    try:
        _, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.terminate()
        _, stderr = process.communicate()
    return stderr


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
            expected_first_param,
            mock_pa(),
            app_settings,
        )

    @pytest.mark.parametrize(
        ("reactor", "expected"),
        (
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
        ),
    )
    def test_reactor_launched(self, reactor, expected):
        options = []
        if reactor is not None:
            options.extend(["-s", f"TWISTED_REACTOR={reactor}"])
        with ProjectDirectory() as directory:
            stderr = run(directory, options)
        assert f"Running with reactor: {expected}".encode() in stderr


def test_settings_option():
    with ProjectDirectory() as directory:
        custom_settings = directory / "testproject" / "custom_settings.py"
        reactor = (
            ("twisted.internet.epollreactor.EPollReactor", "EPollReactor")
            if ASYNCIO_REACTOR_IS_DEFAULT
            else (
                "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
                "AsyncioSelectorReactor",
            )
        )
        custom_settings.write_text(f"TWISTED_REACTOR = {reactor[0]!r}\n")
        options = ["--settings", "testproject.custom_settings"]
        stderr = run(directory, options)
    assert f"Running with reactor: {reactor[1]}".encode() in stderr


def test_settings_import_path_is_empty_string():
    with ProjectDirectory() as directory:
        (directory / "scrapy.cfg").write_text("[settings]\ndefault=\n")
        stderr = run(directory)
    assert b"Cannot find scrapy project settings" in stderr


def test_no_scrapy_cfg():
    with ProjectDirectory() as directory:
        (directory / "scrapy.cfg").unlink()
        stderr = run(directory)
    assert b"Cannot find scrapy.cfg file" in stderr


def test_invalid_setting_definition():
    with ProjectDirectory() as directory:
        options = ["-s", "FOO"]
        stderr = run(directory, options)
    assert b"expected name=value: 'FOO'" in stderr


def test_log_file():
    """Simply tests that nothing breaks by setting a custom log file."""
    with ProjectDirectory() as directory:
        settings = directory / "app_settings.py"
        log_dir = str((directory / "logs").absolute())
        settings.write_text(f"LOG_FILE = 'foo.log'\nLOG_DIR = {log_dir!r}\n")
        options = ["-S", "app_settings"]
        stderr = run(directory, options)
        assert not stderr
