# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

import socket
import zlib

from mo_json import json2value
from mo_logs import Log
from mo_threads import Queue, Thread


class UdpListener(object):

    def __init__(self, port):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.bind(("", port))
                self.queue = Queue("from udp "+str(port))
                self.thread = Thread.run("listen on "+str(port), self._worker)
            except Exception as cause:
                Log.warning("unable to setup listener", cause=cause)

    def _worker(self, please_stop):
        acc = {}
        while not please_stop:
            data, origin = self.sock.recvfrom(1024)
            try:
                json = zlib.decompress(data)
                value = json2value(json.decode('utf8'))
                self.queue.add(value)
            except Exception as cause:
                Log.error("what happens here?")
                acc[origin] = acc.setdefault(origin, b'') + data

    def stop(self):
        self.sock.detach()
        self.sock.close()
        self.thread.stop()