# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import, division, unicode_literals

import logging
from unittest import skipIf

from mo_future import StringIO, PY2
from mo_math import randoms
from mo_testing.fuzzytestcase import FuzzyTestCase
from mo_threads import Till

from mo_logs import logger as log
from tests.utils.udp_listener import UdpListener


class TestLoggers(FuzzyTestCase):
    @skipIf(PY2, "py2 does not have reload")
    def test_logging(self):
        from importlib import reload

        logging.shutdown()
        reload(logging)

        log_stream = StringIO()
        logger = logging.getLogger()
        logging.basicConfig(stream=log_stream, level=logging.INFO)

        log.start(trace=False, settings={"logs": {"log_type": "logger"}})
        log.note("testing")
        while log.main_log.logger.many[0].count < 1:
            Till(seconds=0.1).wait()
        logs = log_stream.getvalue()

        expected = "testing\n"
        self.assertEqual(logs[-len(expected) :], expected)

    def test_graylogger(self):
        offset = randoms.int(1000)
        with UdpListener(12200+offset) as udp:
            log.start(
                settings={"logs": {
                    "class": "graypy.GELFUDPHandler",
                    "host": "localhost",
                    "port": 12200+offset,
                }},
            )
            log.note("testing {{value}}", value="test")
            message = udp.queue.pop()

        self.assertTrue(message.short_message.endswith("testing test"))
        self.assertTrue(message.full_message.endswith("testing test"))
        self.assertTrue(message.file.endswith("test_loggers.py"))
        self.assertEqual(
            message,
            {
                "_value": "test",
                "_function": "test_graylogger",
                "_process_name": "MainProcess",
                "_stack_info": "Null",
                "facility": "mo-logs",
                "level": 6,
                "line": 56,
                "version": "1.0",
            },
        )

    def test_extras(self):
        offset = randoms.int(1000)
        with UdpListener(12200+offset) as udp:
            log.start(
                settings={
                    "logs": {
                        "class": "graypy.GELFUDPHandler",
                        "host": "localhost",
                        "port": 12200 + offset,
                    },
                    "extra": {"some_name": {"v": "some_value"}}
                },
            )
            log.note("testing {{value}}", value="test")
            message = udp.queue.pop()

        self.assertEqual(
            message,
            {
                "_some_name.v":"some_value"
            },
        )
        self.assertTrue(message.file.endswith("test_loggers.py"))

    def test_graylogger_exception(self):
        offset = randoms.int(1000)
        with UdpListener(12200+offset) as udp:
            log.start(
                settings={"logs": {
                    "class": "graypy.GELFUDPHandler",
                    "host": "localhost",
                    "port": 12200+offset,
                }},
            )
            log.warning("testing {{value}}", value="test")
            message = udp.queue.pop()

        self.assertNotIn('test_loggers.py"', message.short_message)
        self.assertIn('test_loggers.py"', message.full_message)

