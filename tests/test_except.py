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
import sys
import unittest
import zlib
from unittest import skip

from mo_dots import listwrap, wrap, Data, to_data
from mo_dots.objects import DataObject
from mo_json import value2json
from mo_logs.exceptions import ERROR, TOO_DEEP
from mo_testing.fuzzytestcase import FuzzyTestCase
from mo_threads import Till

from mo_logs import Except, logger

try:
    from tests.utils.log_usingQueue import StructuredLogger_usingQueue
except Exception as e:
    from test_logs.utils.log_usingQueue import StructuredLogger_usingQueue


class TestExcept(FuzzyTestCase):
    @classmethod
    def setUpClass(cls):
        logger.start({"trace": False})

    def test_trace_of_simple_raises(self):
        try:
            problem_a()
        except Exception as e:
            f = Except.wrap(e)
            self.assertEqual(f.template, "Exception: expected exception")
            for i, m in enumerate(listwrap(f.trace).method):
                if m == "test_trace_of_simple_raises":
                    self.assertEqual(i, 2)
                    break
            else:
                self.fail("expecting stack to show this method")

    def test_full_trace_exists(self):
        try:
            problem_a2()
        except Exception as e:
            cause = e.cause
            self.assertEqual(cause.template, "Exception: expected exception")

            for i, m in enumerate(listwrap(cause.trace).method):
                if m == "test_full_trace_exists":
                    self.assertEqual(i, 2)
                    break
            else:
                self.fail("expecting stack to show this method")

    def test_bad_log_params(self):
        for call in [logger.info, logger.warning, logger.error]:
            with self.assertRaises("was expecting a string template"):
                call({})

    def test_full_trace_on_wrap(self):
        try:
            problem_b()
        except Exception as e:
            cause = Except.wrap(e)
            self.assertEqual(cause.template, "Exception: expected exception")

            for i, m in enumerate(listwrap(cause.trace).method):
                if m == "test_full_trace_on_wrap":
                    self.assertEqual(i, 1)
                    break
            else:
                self.fail("expecting stack to show this method")

    @skip("not implemented")
    def test_local_variable_capture(self):
        a = {"c": "a", "b": "d"}
        b = {"c": "b"}

        A = '{\n    "b": "d",\n    "c": "a"\n}'
        B = '{"c": "b"}'

        log_queue = StructuredLogger_usingQueue("abba")
        backup_log, logger.main_log = logger.main_log, log_queue

        logger.info("{{a}} and {{b}}")
        self.assertEqual(logger.main_log.pop(), A + " and " + B)

        logger.warning("{{a}} and {{b}}", a=a, b=b)
        self.assertEqual(logger.main_log.pop(), A + " and " + B)

    @skip("not implemented")
    def test_missing_local_variable(self):
        a = {"c": "a", "b": "d"}
        b = {"c": "b"}

        log_queue = StructuredLogger_usingQueue("abba")
        backup_log, logger.main_log = logger.main_log, log_queue

        try:
            logger.info("{{c}}")
            logger.error("not expected")
        except Exception as e:
            self.assertTrue("c local is not found" in e)

    def test_warning_keyword_parameters(self):
        a = {"c": "a", "b": "d"}
        b = {"c": "b"}
        params = {"a": a, "b": b}

        WARNING = "WARNING: test"
        CAUSE = "\ncaused by\n\tERROR: Exception: problem"
        A = '{\n    "b": "d",\n    "c": "a"\n}'
        B = '{"c": "b"}'
        AC = "a"
        AB = "d"
        BC = "b"

        log_queue = StructuredLogger_usingQueue("abba")
        backup_log, logger.main_log = logger.main_log, log_queue

        try:
            raise Exception("problem")
        except Exception as e:
            logger.warning("test")
            self.assertEqual(logger.main_log.pop(), WARNING)

            logger.warning("test: {{a}}", a=a)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + A)

            logger.warning("test: {{a}}: {{b}}", a=a, b=b)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + A + ": " + B)

            logger.warning("test", e)
            log_value = logger.main_log.pop()
            self.assertEqual(log_value, WARNING + CAUSE)

            logger.warning("test: {{a}}", a=a, cause=e)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + A + CAUSE)

            logger.warning("test: {{a}}: {{b}}", a=a, b=b, cause=e)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + A + ": " + B + CAUSE)

            logger.warning("test: {{a}}", e, a=a)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + A + CAUSE)

            logger.warning("test: {{a}}: {{b}}", e, a=a, b=b)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + A + ": " + B + CAUSE)

            logger.warning("test: {{a}}", params, e)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + A + CAUSE)

            logger.warning("test: {{a}}: {{b}}", params, e)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + A + ": " + B + CAUSE)

            logger.warning("test: {{a}}: {{b}}", params, e, a=b)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + B + ": " + B + CAUSE)

            logger.warning("test: {{a}}: {{b}}", wrap(params), e, a=b)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + B + ": " + B + CAUSE)

            logger.warning("test: {{a.c}}", a=a)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + AC)

            logger.warning("test: {{a.c}}: {{a.b}}", a=a, b=b)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + AC + ": " + AB)

            logger.warning("test: {{a.c}}: {{b.c}}", a=a, b=b)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + AC + ": " + BC)

            logger.warning("test: {{a.c}}", a=a, cause=e)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + AC + CAUSE)

            logger.warning("test: {{a.c}}: {{b.c}}", a=a, b=b, cause=e)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + AC + ": " + BC + CAUSE)
        finally:
            logger.main_log = backup_log

    def test_note_keyword_parameters(self):
        a = {"c": "a", "b": "d"}
        b = {"c": "b"}
        params = {"a": a, "b": b}

        WARNING = "test"
        A = '{\n    "b": "d",\n    "c": "a"\n}'
        B = '{"c": "b"}'
        AC = "a"
        AB = "d"
        BC = "b"

        # DURING TESTING SOME OTHER THREADS MAY STILL BE WRITING TO THE LOG
        Till(seconds=1).wait()
        # HIGHJACK LOG FOR TESTING OUTPUT
        log_queue = StructuredLogger_usingQueue()
        backup_log, logger.main_log = logger.main_log, log_queue

        try:
            raise Exception("problem")
        except Exception as e:
            logger.info("test")
            self.assertEqual(logger.main_log.pop(), WARNING)

            logger.info("test: {{a}}", a=a)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + A)

            logger.info("test: {{a}}: {{b}}", a=a, b=b)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + A + ": " + B)

            logger.info("test: {{a.c}}", a=a)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + AC)

            logger.info("test: {{a}}: {{b}}", params)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + A + ": " + B)

            logger.info("test: {{a}}: {{b}}", params, a=b)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + B + ": " + B)

            logger.info("test: {{a}}: {{b}}", wrap(params), a=b)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + B + ": " + B)

            logger.info("test: {{a.c}}: {{a.b}}", a=a, b=b)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + AC + ": " + AB)

            logger.info("test: {{a.c}}: {{b.c}}", a=a, b=b)
            self.assertEqual(logger.main_log.pop(), WARNING + ": " + AC + ": " + BC)
        finally:
            logger.main_log = backup_log

    # NORMAL RAISING
    def test_python_raise_from(self):
        def problem_y():
            raise Exception("this is the root cause")

        def problem_x():
            try:
                problem_y()
            except Exception as e:
                raise Exception("this is a problem")

        logging.shutdown()
        from importlib import reload

        reload(logging)

        try:
            problem_x()
        except Exception as e:

            class _catcher(logging.Handler):
                def handle(self, record):
                    o = value2json(DataObject(record))
                    if record:
                        pass
                    if "this is a problem" not in e.args:
                        logger.error("We expect Python to, at least, report the first order problem")
                    if "this is the root cause" in e.args:
                        logger.error("We do not expect Python to report exception chains")

            log = logging.getLogger()
            log.addHandler(_catcher())
            log.exception("problem")

    # NORMAL RE-RAISE
    def test_python_re_raise(self):
        def problem_y():
            raise Exception("this is the root cause")

        def problem_x():
            try:
                problem_y()
            except Exception as f:
                raise f

        try:
            problem_x()
        except Exception as e:
            e = Except.wrap(e)
            self.assertEqual(e.cause, None)  # REALLY, THE CAUSE IS problem_y()

    def test_contains_from_zip_error(self):
        def bad_unzip():
            decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
            return decompressor.decompress(b"invlaid zip file")

        try:
            bad_unzip()
            assert False
        except Exception as e:
            e = Except.wrap(e)
            if "incorrect header check" in e:
                pass
            else:
                assert False

    @skip("this is too complicated for now")
    def test_recursive_loop(self):
        def oh_no():
            try:
                oh_no()
            except BaseException as e:
                logger.error("this is a problem", e)

        try:
            oh_no()
            self.assertTrue(False, "should not happen")
        except Exception as e:
            self.assertIn("recursive", e, "expecting the recursive loop to be identified")

    @skip("this is too complicated for now")
    def test_deep_recursive_loop(self):
        def oh_no():
            try:
                fine1()
            except Exception as e:
                logger.error("this is a problem", e)

        def fine1():
            fine2()

        def fine2():
            oh_no()

        try:
            oh_no()
            self.assertTrue(False, "should not happen")
        except Exception as cause:
            self.assertIn("recursive", cause, "expecting the recursive loop to be identified")

    def test_locals_in_stack_trace(self):
        try:
            problem_c("test_value")
        except Exception as e:
            tb = sys.exc_info()[2]
            self.assertEqual(tb.tb_next.tb_frame.f_locals["a"].value, "test_value")

    def test_many_causes(self):
        try:
            logger.error("problem", cause=to_data([None]))
        except Exception as cause:
            self.assertEqual(cause.message, "problem")
            self.assertIsNone(cause.cause)

    def test_cause_depth_too_deep(self):
        cause = Except(ERROR, "not shown")
        for i in range(TOO_DEEP):
            cause = Except(ERROR, "error", cause=cause)
        text = str(cause)
        self.assertIn("not shown", text)

        cause = Except(ERROR, "error", cause=cause)
        text = str(cause)
        self.assertNotIn("not shown", text)


def problem_a():
    problem_b()


def problem_b():
    raise Exception("expected exception")


def problem_a2():
    try:
        problem_b()
    except Exception as e:
        logger.error("this is a problem", e)


def problem_c(value):
    a = Data(value=value)
    b = "something"
    c = 1 / 0


if __name__ == "__main__":
    try:
        Log.start()
        unittest.main()
    finally:
        Log.stop()
