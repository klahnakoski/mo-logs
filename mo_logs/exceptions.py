# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import sys
from datetime import datetime

from mo_dots import Null, is_data, listwrap, unwraplist, to_data, dict_to_data
from mo_future import is_text
from mo_logs.strings import CR, expand_template, indent

FATAL = "FATAL"
ERROR = "ERROR"
WARNING = "WARNING"
ALARM = "ALARM"
UNEXPECTED = "UNEXPECTED"
INFO = "INFO"
NOTE = "NOTE"
TOO_DEEP = 50  # MAXIMUM DEPTH OF CAUSAL CHAIN


class LogItem(object):
    def __init__(self, severity, template, params, timestamp):
        self.severity = severity
        self.template = template
        self.params = params
        self.timestamp = timestamp

    def __data__(self):
        return dict_to_data(self.__dict__)


class Except(Exception):
    def __init__(self, severity=ERROR, template=Null, params=Null, cause=Null, trace=Null, **_):
        self.timestamp = datetime.utcnow()
        if severity == None:
            raise ValueError("expecting severity to not be None")

        self.cause = unwraplist([Except.wrap(c, stack_depth=2) for c in listwrap(cause)])

        Exception.__init__(self)
        self.severity = severity
        self.template = template
        self.params = params
        self.trace = trace or get_stacktrace(2)

    @classmethod
    def wrap(cls, e, stack_depth=0):
        """
        ENSURE THE STACKTRACE AND CAUSAL CHAIN IS CAPTURED, PLUS ADD FEATURES OF Except

        :param e: AN EXCEPTION OF ANY TYPE
        :param stack_depth: HOW MANY CALLS TO TAKE OFF THE TOP OF THE STACK TRACE
        :return: A Except OBJECT OF THE SAME
        """
        if e == None:
            return Null
        elif isinstance(e, (list, Except)):
            return e
        elif is_data(e):
            e.cause = unwraplist([Except.wrap(c) for c in listwrap(e.cause)])
            return Except(**e)
        else:
            tb = getattr(e, "__traceback__", None)
            if tb is not None:
                trace = _parse_traceback(tb)
            else:
                trace = get_traceback(0)

            cause = Except.wrap(getattr(e, "__cause__", None))
            message = getattr(e, "message", None)
            if message:
                output = Except(
                    severity=ERROR, template=f"{e.__class__.__name__}: {message}", trace=trace, cause=cause,
                )
            else:
                output = Except(
                    severity=ERROR, template=f"{e.__class__.__name__}: {e}", trace=trace, cause=cause,
                )

            trace = get_stacktrace(stack_depth + 2)  # +2 = to remove the caller, and it's call to this' Except.wrap()
            output.trace.extend(trace)
            return output

    @property
    def message(self):
        return expand_template(self.template, self.params)

    def __contains__(self, value):
        if is_text(value):
            if value in self.template or value in self.message:
                return True

        if self.severity == value:
            return True
        for c in listwrap(self.cause):
            if value in c:
                return True
        return False

    def __str__(self):
        return self._desc_text(0)

    def _desc_text(self, depth):
        output = self.severity + ": " + self.template + CR
        if self.params:
            try:
                output = expand_template(output, self.params)
            except Exception as cause:
                return self.template

        if self.trace:
            output += indent(format_trace(self.trace))

        output += self._cause_text(depth)
        return output

    __repr__ = __str__

    @property
    def trace_text(self):
        return format_trace(self.trace)

    @property
    def cause_text(self):
        return self._cause_text(0)

    def _cause_text(self, depth):
        if not self.cause:
            return ""
        if depth >= TOO_DEEP:
            return "and caused by\n\t...\n"

        cause_strings = []
        for c in listwrap(self.cause):
            try:
                if isinstance(c, Except):
                    cause_strings.append(c._desc_text(depth+1))
                else:
                    cause_strings.append(str(c))
            except Exception as cause:
                sys.stderr.write(f"Problem serializing cause {cause}")

        return "caused by\n\t" + "and caused by\n\t".join(cause_strings)

    def __data__(self):
        output = to_data({k: getattr(self, k) for k in vars(self)})
        output.cause = unwraplist([c.__data__() for c in listwrap(output.cause)])
        return output


def get_stacktrace(start=0):
    """
    SNAGGED FROM traceback.py
    Altered to return Data

    Extract the raw traceback from the current stack frame.

    Each item in the returned list is a quadruple (filename,
    line number, function name, text), and the entries are in order
    from newest to oldest
    """
    try:
        raise ZeroDivisionError
    except ZeroDivisionError:
        trace = sys.exc_info()[2]
        f = trace.tb_frame.f_back

    for i in range(start):
        f = f.f_back

    stack = []
    while f is not None:
        stack.append({
            "file": f.f_code.co_filename,
            "line": f.f_lineno,
            "method": f.f_code.co_name,
        })
        f = f.f_back
    return stack


def get_traceback(start):
    """
    SNAGGED FROM traceback.py

    RETURN list OF dicts DESCRIBING THE STACK TRACE
    """
    tb = sys.exc_info()[2]
    for i in range(start):
        tb = tb.tb_next
    return _parse_traceback(tb)


def _parse_traceback(tb):
    trace = []
    while tb is not None:
        f = tb.tb_frame
        trace.append({
            "file": f.f_code.co_filename,
            "line": tb.tb_lineno,
            "method": f.f_code.co_name,
        })
        tb = tb.tb_next
    trace.reverse()
    return trace


def format_trace(tbs, start=0):
    return "".join(expand_template('File ""{file}"", line {line}, in {method}\n', d) for d in tbs[start::])


class Suppress(object):
    """
    IGNORE EXCEPTIONS
    """

    def __init__(self, exception_type):
        self.severity = exception_type

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not exc_val or isinstance(exc_val, self.severity):
            return True


suppress_exception = Suppress(Exception)


class Explanation(object):
    """
    EXPLAIN THE ACTION BEING TAKEN
    IF THERE IS AN EXCEPTION WRAP IT WITH THE EXPLANATION
    CHAIN EXCEPTION AND RE-RAISE
    """

    def __init__(self, template, debug=False, **more_params):  # human readable template
        self.debug = debug
        self.template = template
        self.more_params = more_params

    def __enter__(self):
        if self.debug:
            from mo_logs import logger

            logger.info(self.template, default_params=self.more_params, stack_depth=1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, Exception):
            from mo_logs import logger

            logger.error(
                template="Failure in " + self.template, default_params=self.more_params, cause=exc_val, stack_depth=1,
            )

            return True


class WarnOnException(object):
    """
    EXPLAIN THE ACTION BEING TAKEN
    IF THERE IS AN EXCEPTION WRAP ISSUE A WARNING
    """

    def __init__(self, template, debug=False, **more_params):  # human readable template
        self.debug = debug
        self.template = template
        self.more_params = more_params

    def __enter__(self):
        if self.debug:
            from mo_logs import logger

            logger.info(self.template, default_params=self.more_params, stack_depth=1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, Exception):
            from mo_logs import logger

            logger.warning(
                template="Ignored failure while " + self.template,
                default_params=self.more_params,
                cause=exc_val,
                stack_depth=1,
            )

            return True


class AssertNoException(object):
    """
    EXPECT NO EXCEPTION IN THIS BLOCK
    """

    def __init__(self):
        pass

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, Exception):
            from mo_logs import logger

            logger.error(template="Not expected to fail", cause=exc_val, stack_depth=1)

            return True


assert_no_exception = AssertNoException()
