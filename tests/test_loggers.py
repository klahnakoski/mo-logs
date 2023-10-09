# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import logging

from mo_dots import Data
from mo_future import StringIO
from mo_kwargs import override
from mo_math import randoms
from mo_testing.fuzzytestcase import FuzzyTestCase, add_error_reporting
from mo_threads import Till

from mo_logs import logger as log, register_logger
from mo_logs.log_usingNothing import StructuredLogger
from mo_logs.strings import expand_template
from tests.utils.udp_listener import UdpListener

UDP_PORT_RANGE = Data(FROM=12200, LENGTH=4000)


@add_error_reporting
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
        port = UDP_PORT_RANGE.FROM + randoms.int(UDP_PORT_RANGE.LENGTH)
        with UdpListener(port) as udp:
            log.start(settings={"logs": {"class": "graypy.GELFUDPHandler", "host": "localhost", "port": port}},)
            log.note("testing {{value}}", value="test")
            message = udp.queue.pop()

        self.assertTrue(message["short_message"].endswith("testing test"))
        self.assertTrue(message["full_message"].endswith("testing test"))
        self.assertTrue(message["file"].endswith("test_loggers.py"))

        print(message)
        self.assertEqual(
            message,
            {
                "_value": "test",
                "_function": "test_graylogger",
                "_process_name": "MainProcess",
                "facility": "mo-logs",
                "level": 6,
                "line": 58,  # <-- CAREFUL WHEN REFORMATTING THIS FILE, THIS CAN CHANGE
                "version": "1.0",
                "_thread_name": "Main Thread",
            },
        )
        self.assertIsNone(message["_stack_info"])

    def test_graylogger_for_debugging(self):
        port = UDP_PORT_RANGE.FROM + randoms.int(UDP_PORT_RANGE.LENGTH)
        with UdpListener(port) as udp:
            log.main_log = log.new_instance({"class": "graypy.GELFUDPHandler", "host": "localhost", "port": port})
            log.note("testing {{value}}", value="test")
            message = udp.queue.pop()

        self.assertTrue(message["short_message"].endswith("testing test"))
        self.assertTrue(message["full_message"].endswith("testing test"))
        self.assertTrue(message["file"].endswith("test_loggers.py"))

        print(message)
        self.assertEqual(
            message,
            {
                "_value": "test",
                "_function": "test_graylogger_for_debugging",
                "_process_name": "MainProcess",
                "facility": "mo-logs",
                "level": 6,
                "version": "1.0",
                "_thread_name": "Main Thread",
            },
        )
        self.assertIsNone(message["_stack_info"])

    def test_extras(self):
        port = UDP_PORT_RANGE.FROM + randoms.int(UDP_PORT_RANGE.LENGTH)
        with UdpListener(port) as udp:
            log.start(
                settings={
                    "logs": {"class": "graypy.GELFUDPHandler", "host": "localhost", "port": port,},
                    "extra": {"some_name": {"v": "some_value"}},
                },
            )
            log.note("testing {{value}}", value="test")
            message = udp.queue.pop()

        self.assertIsInstance(message, dict)
        self.assertEqual(message, {"_some_name.v": "some_value"})
        self.assertTrue(message["file"].endswith("test_loggers.py"))

    def test_graylogger_exception(self):
        port = randoms.int(UDP_PORT_RANGE.FROM + UDP_PORT_RANGE.LENGTH)
        with UdpListener(port) as udp:
            log.start(settings={"logs": {"class": "graypy.GELFUDPHandler", "host": "localhost", "port": port,}},)
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

    def test_single_braces(self):
        log.trace = True
        logger = log.main_log = LogUsingLines()
        log.note("this is a {test}", test="test")
        # EG: 'kyle-win10 (pid 14900) - 2023-05-29 12:36:09.304071 - Main Thread - "C:\\Users\\kyle\\code\\mo-logs\\tests\\test_loggers.py:162" - (test_simple_logging) - this is a test'
        self.assertIn("(pid ", logger.lines[0])
        self.assertIn(" - Main Thread - ", logger.lines[0])
        self.assertIn(" - (test_single_braces) - ", logger.lines[0])
        self.assertIn(" - this is a test", logger.lines[0])
        self.assertIn("test_loggers.py:", logger.lines[0])

    def test_bad_log_call(self):
        log.start(trace=True)
        with self.assertRaises("Expecting logger call to be static"):
            for v in ["1", "2"]:
                log.note(v)

    def test_simple_tet(self):
        log.start(trace=False)
        logger = log.main_log = LogUsingLines()
        log.note("Timer start: get modules' status")
        self.assertEqual("Timer start: get modules' status", logger.lines[0])


class LogUsingArray(StructuredLogger):
    @override
    def __init__(self, kwargs=None):
        self.lines = []

    def write(self, template, params):
        self.lines.append((template, params))


class LogUsingLines(StructuredLogger):
    @override
    def __init__(self, kwargs=None):
        self.lines = []

    def write(self, template, params):
        value = expand_template(template, params)
        self.lines.append(value)


register_logger("array", LogUsingArray)
