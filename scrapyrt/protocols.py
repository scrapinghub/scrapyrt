# -*- coding: utf-8 -*-
from twisted.internet.protocol import Protocol


class HTTPReturner(Protocol):
    def __init__(self, finished):
        self._data = ""
        self.deferred = finished

    def dataReceived(self, data):
        self._data += data

    def connectionLost(self, reason):
        self.deferred.callback(self._data)
