# -*- coding: utf-8 -*-
import six
from subprocess import Popen, PIPE
from six.moves.urllib.parse import urljoin
import fcntl
import os
import shutil
import socket
import sys
import tempfile
import time

import port_for

from . import SAMPLE_DATA
from .utils import get_testenv, generate_project

DEVNULL = open(os.devnull, 'wb')


class BaseTestServer(object):

    def __init__(self, host='localhost', port=None, cwd=None, shell=False,
                 stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL):
        self.host = host
        self.port = port or port_for.select_random()
        self.proc = None
        self.shell = shell
        self.cwd = cwd
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        if six.PY2:
            command = 'SimpleHTTPServer'
        else:
            command = 'http.server'
        self.arguments = [
            sys.executable, '-u', '-m', command, str(self.port)
        ]

    def start(self):
        self.proc = Popen(
            self.arguments,
            stdin=self.stdin,
            stdout=self.stdout,
            stderr=self.stderr,
            shell=self.shell,
            cwd=self.cwd,
            env=get_testenv()
        )
        self.proc.poll()
        if self.proc.returncode:
            msg = (
                "unable to start server. error code: %d - stderr follows: \n%s"
            ) % (self.proc.returncode, self.proc.stderr.read())
            raise RuntimeError(msg)
        try:
            self._wait_for_port()
        finally:
            print(self._non_block_read(self.proc.stderr))
            pass

    def stop(self):
        if self.proc is None:
            raise RuntimeError("Server wasn't started")
        self.proc.kill()
        self.proc.wait()
        self.proc = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def url(self, path=''):
        return urljoin('http://{}:{}'.format(self.host, self.port), path)

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
        raise RuntimeError("Port %d is not open" % self.port)

    @staticmethod
    def _non_block_read(output):
        if output is None:
            return ''
        fd = output.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        try:
            return output.read()
        except Exception:
            return ''


class ScrapyrtTestServer(BaseTestServer):

    def __init__(self, site=None, *args, **kwargs):
        super(ScrapyrtTestServer, self).__init__(*args, **kwargs)
        self.arguments = [
            sys.executable, '-m', 'scrapyrt.cmdline', '-p', str(self.port)
        ]
        self.stderr = PIPE
        self.tmp_dir = tempfile.mkdtemp()
        self.cwd = os.path.join(self.tmp_dir, 'testproject')
        generate_project(self.cwd, site=site)

    def stop(self):
        super(ScrapyrtTestServer, self).stop()
        shutil.rmtree(self.tmp_dir)


class MockServer(BaseTestServer):

    def __init__(self, *args, **kwargs):
        super(MockServer, self).__init__(*args, **kwargs)
        self.cwd = os.path.join(SAMPLE_DATA, 'testsite')
