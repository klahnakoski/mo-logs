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

from mo_future import StringIO
from mo_kwargs import override

from mo_logs.log_usingNothing import StructuredLogger
from mo_math import randoms
from mo_testing.fuzzytestcase import FuzzyTestCase
from mo_threads import Till

from mo_logs import logger as log, register_logger
from tests.utils.udp_listener import UdpListener


class TestLoggers(FuzzyTestCase):
    def setUp(self):
        log.start()

    def tearDown(self):
        log.stop()

    def test_logging(self):
        from importlib import reload

        logging.shutdown()
        reload(logging)

        log_stream = StringIO()
        logging.getLogger()
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
        with UdpListener(12200 + offset) as udp:
            log.start(
                settings={"logs": {
                    "class": "graypy.GELFUDPHandler",
                    "host": "localhost",
                    "port": 12200 + offset,
                }},
            )
            log.note("testing {{value}}", value="test")
            message = udp.queue.pop()

        self.assertTrue(message["short_message"].endswith("testing test"))
        self.assertTrue(message["full_message"].endswith("testing test"))
        self.assertTrue(message["file"].endswith("test_loggers.py"))
        self.assertEqual(
            message,
            {
                "_value": "test",
                "_function": "test_graylogger",
                "_process_name": "MainProcess",
                "facility": "mo-logs",
                "level": 6,
                "line": 63,
                "version": "1.0",
            },
        )
        self.assertIsNone(message["_stack_info"])

    def test_extras(self):
        offset = randoms.int(1000)
        with UdpListener(12200 + offset) as udp:
            log.start(
                settings={
                    "logs": {
                        "class": "graypy.GELFUDPHandler",
                        "host": "localhost",
                        "port": 12200 + offset,
                    },
                    "extra": {"some_name": {"v": "some_value"}},
                },
            )
            log.note("testing {{value}}", value="test")
            message = udp.queue.pop()

        self.assertEqual(
            message, {"_some_name.v": "some_value"},
        )
        self.assertTrue(message["file"].endswith("test_loggers.py"))

    def test_graylogger_exception(self):
        offset = randoms.int(1000)
        with UdpListener(12200 + offset) as udp:
            log.start(
                settings={"logs": {
                    "class": "graypy.GELFUDPHandler",
                    "host": "localhost",
                    "port": 12200 + offset,
                }},
            )
            log.warning("testing {{value}}", value="test")
            message = udp.queue.pop()

        self.assertNotIn('test_loggers.py"', message["short_message"])
        self.assertIn('test_loggers.py"', message["full_message"])
        self.assertIsInstance(message["_stack_info"], str)

    def test_exc_info(self):
        log.start(logs={"log_type": "array"})
        try:
            raise Exception("kyle")
        except Exception:
            log.warning("report", exc_info=True)
            Till(seconds=0.2).wait()

        template, detail = log.main_log.logger.many[0].lines[0]
        self.assertIn("kyle", detail.cause.template)
        self.assertIn("test_loggers.py", detail.cause.trace[0].file)

    def test_exc_info2(self):
        log.start(logs={"log_type": "array"})
        try:
            raise Exception("kyle")
        except Exception as cause:
            log.warning("report", exc_info=cause)
            Till(seconds=0.2).wait()

        template, detail = log.main_log.logger.many[0].lines[0]
        self.assertIn("kyle", detail.cause.template)
        self.assertIn("test_loggers.py", detail.cause.trace[0].file)


class LogUsingArray(StructuredLogger):
    @override
    def __init__(self, kwargs=None):
        self.lines = []

    def write(self, template, params):
        self.lines.append((template, params))


register_logger("array", LogUsingArray)
