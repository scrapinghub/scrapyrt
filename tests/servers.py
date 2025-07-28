import fcntl
import os
import shutil
import socket
import sys
import tempfile
import time
from contextlib import suppress
from pathlib import Path
from subprocess import DEVNULL, PIPE, Popen
from urllib.parse import urljoin

import port_for

from . import TESTS_PATH
from .utils import generate_project, get_testenv


class BaseTestServer:
    def __init__(  # noqa: PLR0913
        self,
        host="localhost",
        port=None,
        cwd=None,
        shell=False,
        stdin=DEVNULL,
        stdout=DEVNULL,
        stderr=DEVNULL,
    ):
        self.host = host
        self.port = port or port_for.select_random()
        self.proc = None
        self.shell = shell
        self.cwd = cwd
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

        self.arguments = ["flask", "run", "-p", str(self.port)]

    def start(self):
        self.proc = Popen(
            self.arguments,
            stdin=self.stdin,
            stdout=self.stdout,
            stderr=self.stderr,
            shell=self.shell,
            cwd=self.cwd,
            env=get_testenv(),
        )
        self.proc.poll()
        if self.proc.returncode:
            assert self.proc.stderr is not None
            raise RuntimeError(
                f"unable to start server. error code: {self.proc.returncode} "
                f"- stderr follows: \n{self.proc.stderr.read().decode()}",
            )
        try:
            self._wait_for_port()
        finally:
            print(self._non_block_read(self.proc.stderr))

    def stop(self):
        if self.proc is None:
            raise RuntimeError("Server wasn't started")
        self.proc.terminate()
        self.proc.wait()
        if self.proc.stderr and hasattr(self.proc.stderr, "close"):
            with suppress(Exception):
                self.proc.stderr.close()
        self.proc = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def url(self, path=""):
        return urljoin(f"http://{self.host}:{self.port}", path)

    def _wait_for_port(self, delay=0.1, attempts=20):
        """Imports could take some time, server opens port with some delay."""
        while attempts > 0:
            s = socket.socket()
            try:
                s.connect((self.host, self.port))
            except Exception:
                time.sleep(delay)
                attempts -= 1
            else:
                return
            finally:
                s.close()
        raise RuntimeError(f"Port {self.port} is not open")

    @staticmethod
    def _non_block_read(output):
        if output is None:
            return ""
        fd = output.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            return output.read()
        except Exception:
            return ""


class ScrapyrtTestServer(BaseTestServer):
    def __init__(self, site, *args, project_generator=generate_project, **kwargs):
        super().__init__(*args, **kwargs)
        self.arguments = [
            sys.executable,
            "-m",
            "scrapyrt.cmdline",
            "-p",
            str(self.port),
        ]
        self.stderr = PIPE
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.cwd = self.tmp_dir
        project_generator(self.cwd, site=site)
        self.site: MockServer = site

    def stop(self):
        super().stop()
        shutil.rmtree(self.tmp_dir)


class MockServer(BaseTestServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cwd = TESTS_PATH / "testsite"
