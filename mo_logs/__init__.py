# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import os
import sys
from datetime import datetime
from threading import current_thread

from mo_dots import Data, coalesce, listwrap, unwraplist, dict_to_data, is_data, to_data
from mo_future import is_text, STDOUT
from mo_imports import delay_import
from mo_kwargs import override

from mo_logs import constants as _constants, exceptions, strings
from mo_logs.exceptions import (
    Except,
    LogItem,
    suppress_exception,
    format_trace,
    WARNING,
    get_stacktrace,
)
from mo_logs.log_usingStream import StructuredLogger_usingStream
from mo_logs.strings import CR, indent

STACKTRACE = "\n{trace_text|indent}\n{cause_text}"

StructuredLogger_usingMulti = delay_import("mo_logs.log_usingMulti.StructuredLogger_usingMulti")
StructuredLogger_usingThread = delay_import("mo_logs.log_usingThread.StructuredLogger_usingThread")

startup_read_settings = delay_import("mo_logs.startup.read_settings")

all_log_callers = {}


class Log(object):
    """
    FOR STRUCTURED LOGGING AND EXCEPTION CHAINING
    """

    trace = False
    main_log = StructuredLogger_usingStream(STDOUT)
    logging_multi = None
    profiler = None  # simple pypy-friendly profiler
    error_mode = False  # prevent error loops
    extra = {}

    @classmethod
    @override("settings")
    def start(
        cls, trace=False, cprofile=False, constants=None, logs=None, extra=None, app_name=None, settings=None,
    ):
        """
        RUN ME FIRST TO SETUP THE THREADED LOGGING
        https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/

        :param trace: SHOW MORE DETAILS IN EVERY LOG LINE (default False)
        :param cprofile: True==ENABLE THE C-PROFILER THAT COMES WITH PYTHON (default False)
                         USE THE LONG FORM TO SET THE FILENAME {"enabled": True, "filename": "cprofile.tab"}
        :param constants: UPDATE MODULE CONSTANTS AT STARTUP (PRIMARILY INTENDED TO CHANGE DEBUG STATE)
        :param logs: LIST OF PARAMETERS FOR LOGGER(S)
        :param extra: ADDITIONAL DATA TO BE INCLUDED IN EVERY LOG LINE
        :param app_name: GIVE THIS APP A NAME, AND RETURN A CONTEXT MANAGER
        :param settings: ALL THE ABOVE PARAMETERS
        :return:
        """
        if app_name:
            return LoggingContext(app_name)

        Log.stop()

        cls.settings = settings
        cls.trace = trace

        # ENABLE CPROFILE
        if cprofile is False:
            cprofile = settings.cprofile = Data(enabled=False)
        elif cprofile is True:
            cprofile = settings.cprofile = Data(enabled=True, filename="cprofile.tab")
        if is_data(cprofile) and cprofile.enabled:
            from mo_threads import profiles

            profiles.enable_profilers(settings.cprofile.filename)

        if constants:
            _constants.set(constants)

        logs = coalesce(settings.log, logs)
        if logs:
            cls.logging_multi = StructuredLogger_usingMulti()
            for log in listwrap(logs):
                Log._add_log(Log.new_instance(log))

            from mo_logs.log_usingThread import StructuredLogger_usingThread

            old_log, cls.main_log = (
                cls.main_log,
                StructuredLogger_usingThread(cls.logging_multi),
            )
            old_log.stop()
        cls.extra = extra or {}

    @classmethod
    def stop(cls):
        """
        DECONSTRUCTS ANY LOGGING, AND RETURNS TO DIRECT-TO-stdout LOGGING
        EXECUTING MULUTIPLE TIMES IN A ROW IS SAFE, IT HAS NO NET EFFECT, IT STILL LOGS TO stdout
        :return: NOTHING
        """
        old_log, cls.main_log = cls.main_log, StructuredLogger_usingStream(STDOUT)
        old_log.stop()
        cls.trace = False
        cls.cprofile = False

    @classmethod
    @override("settings")
    def new_instance(cls, log_type=None, settings=None):
        if settings["class"]:
            from mo_logs.log_usingHandler import StructuredLogger_usingHandler

            return StructuredLogger_usingHandler(settings)

        clazz = _known_loggers.get(log_type.lower())
        if clazz:
            return clazz(settings)
        logger.error("Log type of {config|json} is not recognized", config=settings)

    @classmethod
    def _add_log(cls, log):
        cls.logging_multi.add_log(log)

    @classmethod
    def set_logger(cls, logger):
        if cls.logging_multi:
            cls.logging_multi.add_log(logger)
        else:
            from mo_logs.log_usingThread import StructuredLogger_usingThread

            old_log, cls.main_log = cls.main_log, StructuredLogger_usingThread(logger)
            old_log.stop()

    @classmethod
    def note(cls, template, default_params={}, *, stack_depth=0, static_template=True, **more_params):
        """
        :param template: *string* human readable string with placeholders for parameters
        :param default_params: *dict* parameters to fill in template
        :param stack_depth:  *int* how many calls you want popped off the stack to report the *true* caller
        :param static_template: *bool* if True, then the template is static, and optimization can be done
        :param more_params: *any more parameters (which will overwrite default_params)
        :return:
        """
        timestamp = datetime.utcnow()
        if not is_text(template):
            logger.error("logger.info was expecting a string template")

        Log._annotate(
            LogItem(
                severity=exceptions.NOTE,
                template=template,
                params=dict(default_params, **more_params),
                timestamp=timestamp,
            ),
            stack_depth + 1,
            static_template
        )

    info = note

    @classmethod
    def alarm(cls, template, default_params={}, *, stack_depth=0, static_template=True, **more_params):
        """
        :param template: *string* human readable string with placeholders for parameters
        :param default_params: *dict* parameters to fill in template
        :param stack_depth:  *int* how many calls you want popped off the stack to report the *true* caller
        :param more_params: more parameters (which will overwrite default_params)
        :return:
        """
        timestamp = datetime.utcnow()
        template = ("*" * 80) + CR + indent(template, prefix="** ").strip() + CR + ("*" * 80)
        Log._annotate(
            LogItem(
                severity=exceptions.ALARM,
                template=template,
                params=dict(default_params, **more_params),
                timestamp=timestamp,
            ),
            stack_depth + 1,
            static_template
        )

    alert = alarm

    @classmethod
    def warning(
        cls,
        template: str,  # human readable string with placeholders for parameters
        default_params={},  # parameters to fill in template
        cause=None,  # for chaining
        *,
        stack_depth=0,  # how many calls you want popped off the stack to report the *true* caller
        log_severity=WARNING,  # set the logging severity
        exc_info=None,  # used by python logging as the cause
        static_template=True,
        **more_params,  # any more parameters (which will overwrite default_params)
    ):
        if exc_info is True:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            exc_info = Except.wrap(exc_value)
        if not is_text(template):
            logger.error("logger.warning was expecting a string template")
        if "values" in more_params.keys():
            logger.error("Can not handle a logging parameter by name `values`")

        if isinstance(default_params, BaseException):
            cause = default_params
            default_params = {}

        params = to_data(dict(default_params, **more_params))
        cause = unwraplist([Except.wrap(c, stack_depth=2) for c in listwrap(cause or exc_info)])
        trace = exceptions.get_stacktrace(stack_depth + 1)

        e = Except(severity=log_severity, template=template, params=params, cause=cause, trace=trace,)
        Log._annotate(e, stack_depth + 1, static_template)

    warn = warning

    @classmethod
    def error(
        cls,
        template,  # human readable template
        default_params={},  # parameters for template
        *,
        cause=None,  # pausible cause
        stack_depth=0,
        exc_info=None,  # used by python logging as the cause
        **more_params,
    ):
        """
        raise an exception with a trace for the cause too

        :param template: *string* human readable string with placeholders for parameters
        :param default_params: *dict* parameters to fill in template
        :param cause: *Exception* for chaining
        :param stack_depth:  *int* how many calls you want popped off the stack to report the *true* caller
        :param exc_info: *Exception* alternate to cause (used by other logging libs)
        :param more_params: *any more parameters (which will overwrite default_params)
        :return:
        """
        if not is_text(template):
            # sys.stderr.write(str("logger.error was expecting a string template"))
            logger.error("logger.error was expecting a string template")
        if "values" in more_params.keys():
            logger.error("Can not handle a logging parameter by name `values`")
        if exc_info is True:
            exc_info = Except.wrap(sys.exc_info())

        if isinstance(default_params, BaseException):
            cause = default_params
            default_params = {}

        params = to_data(dict(default_params, **more_params))
        cause = unwraplist([Except.wrap(c, stack_depth=2) for c in listwrap(cause or exc_info)])
        trace = exceptions.get_stacktrace(stack_depth + 1)

        e = Except(severity=exceptions.ERROR, template=template, params=params, cause=cause, trace=trace,)
        raise_from_none(e)

    @classmethod
    def _annotate(cls, item, stack_depth, static_template):
        """
        :param item:  A LogItem THE TYPE OF MESSAGE
        :param stack_depth: FOR TRACKING WHAT LINE THIS CAME FROM
        :return:
        """
        given_template = item.template
        given_template = strings.limit(given_template, 10000)
        param_template = "".join(f"{text}{{params.{code}}}" if code else text for text, code in strings.parse_template(given_template))

        if isinstance(item, Except):
            param_template = "{severity}: " + param_template + STACKTRACE
            temp = item.__data__()
            temp.trace_text = item.trace_text
            temp.cause_text = item.cause_text
            item = temp
        else:
            item = item.__data__()

        if not param_template.startswith(CR) and CR in param_template:
            param_template = CR + param_template

        if cls.trace:
            item.machine = machine_metadata()
            log_format = item.template = (
                "{machine.name} (pid {machine.pid}) - {timestamp|datetime} -"
                ' {thread.name} - ""{location.file}:{location.line}"" -'
                " ({location.method}) - "
                + param_template
            )
            f = sys._getframe(stack_depth + 1)
            item.location = {
                "line": f.f_lineno,
                "file": f.f_code.co_filename,
                "method": f.f_code.co_name,
            }
            if static_template:
                last_caller_loc = (f.f_code.co_filename, f.f_lineno)
                prev_template = all_log_callers.get(last_caller_loc)
                if prev_template != given_template:
                    if prev_template:
                        raise Except(
                            template="Expecting logger call to be static: was {a|quote} now {b|quote}",
                            params={"a": prev_template, "b": given_template},
                            trace=get_stacktrace(stack_depth + 1),
                        )
                    all_log_callers[last_caller_loc] = given_template
            thread = current_thread()
            item.thread = {"name": thread.name, "id": thread.ident}
        else:
            log_format = param_template
            # log_format = item.template = "{timestamp|datetime} - " + template

        item.params = {**cls.extra, **item.params}
        cls.main_log.write(log_format, item)

    def write(self):
        raise NotImplementedError


logger = Log


def getLogger(*args, **kwargs):
    return logger


class LoggingContext:
    def __init__(self, app_name=None):
        self.app_name = app_name
        self.config = None

    def __enter__(self):
        self.config = config = startup_read_settings()
        from mo_logs import constants

        constants.set(config.constants)
        Log.start(config.debug)
        return config

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            logger.warning(
                "Problem with {name}! Shutting down.", name=self.app_name, cause=exc_val,
            )
        Log.stop()


def _same_frame(frameA, frameB):
    return (frameA.line, frameA.file) == (frameB.line, frameB.file)


# GET THE MACHINE METADATA
_machine_metadata = None


def machine_metadata():
    global _machine_metadata
    if _machine_metadata:
        return _machine_metadata

    import platform

    _machine_metadata = dict_to_data({
        "pid": os.getpid(),
        "python": platform.python_implementation(),
        "os": (platform.system() + platform.release()).strip(),
        "name": platform.node(),
    })
    return _machine_metadata


def raise_from_none(e):
    raise e from None


def _using_logger(config):
    from mo_logs.log_usingLogger import StructuredLogger_usingLogger

    return StructuredLogger_usingLogger(config)


def _using_file(config):
    from mo_logs.log_usingFile import StructuredLogger_usingFile

    if config.file:
        return StructuredLogger_usingFile(config.file)
    if config.filename:
        return StructuredLogger_usingFile(config.filename)


def _using_console(config):
    from mo_logs.log_usingThread import StructuredLogger_usingThread

    return StructuredLogger_usingThread(StructuredLogger_usingStream(STDOUT))


def _using_mozlog(config):
    from mo_logs.log_usingMozLog import StructuredLogger_usingMozLog

    return StructuredLogger_usingMozLog(STDOUT, coalesce(config.app_name, config.appname))


def _using_stream(config):
    from mo_logs.log_usingThread import StructuredLogger_usingThread

    return StructuredLogger_usingThread(StructuredLogger_usingStream(config.stream))


def _using_elasticsearch(config):
    from jx_elasticsearch.log_usingElasticSearch import StructuredLogger_usingElasticSearch

    return StructuredLogger_usingElasticSearch(config)


def _using_email(config):
    from mo_logs.log_usingEmail import StructuredLogger_usingEmail

    return StructuredLogger_usingEmail(config)


def _using_ses(config):
    from mo_logs.log_usingSES import StructuredLogger_usingSES

    return StructuredLogger_usingSES(config)


def _using_nothing(config):
    from mo_logs.log_usingNothing import StructuredLogger

    return StructuredLogger()


_known_loggers = {
    "logger": _using_logger,
    "nothing": _using_nothing,
    "none": _using_nothing,
    "null": _using_nothing,
    "file": _using_file,
    "console": _using_console,
    "mozlog": _using_mozlog,
    "stream": _using_stream,
    "elasticsearch": _using_elasticsearch,
    "email": _using_email,
    "ses": _using_ses,
}


def register_logger(name, factory):
    _known_loggers[name] = factory
