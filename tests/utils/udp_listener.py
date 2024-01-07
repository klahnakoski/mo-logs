# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import json
import socket
import zlib

from mo_math import randoms

from mo_logs import Log, Except
from mo_threads import Queue, Thread, Till


class UdpListener(object):
    def \
            __init__(self, port):
        self.port = port
        self.sock = None
        self.queue = None
        self.thread = None

    def __enter__(self):
        while True:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.bind(("", self.port))
                self.queue = Queue("from udp " + str(self.port))
                self.thread = Thread.run("listen on " + str(self.port), self._worker)
                break
            except Exception as cause:
                cause = Except.wrap(cause)
                if "[Errno 13] Permission denied" in cause:
                    # happens on travis occasionally, and then an infinite loop
                    raise cause
                self.sock.close()
                Log.warning("unable to setup listener", cause=cause)
                Till(seconds=randoms.int(10)).wait()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.thread.stop()
        self.sock.close()
        self.thread.join()

    def _worker(self, please_stop):
        acc = {}
        try:
            while not please_stop:
                try:
                    self.sock.settimeout(10)
                    data, origin = self.sock.recvfrom(1024)
                except Exception as cause:
                    if please_stop:
                        break
                    raise Log.error("unexpected problem with receive", cause=cause)

                try:
                    jsons = zlib.decompress(data)
                    value = json.loads(jsons.decode("utf8"))
                    self.queue.add(value)
                except Exception as cause:
                    Log.error("what happens here?", cause=cause)
                    acc[origin] = acc.setdefault(origin, b"") + data
        finally:
            self.queue.close()
