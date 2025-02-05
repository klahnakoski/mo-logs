# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import os
from threading import current_thread

from mo_dots import Data, coalesce, dict_to_data
from mo_future import STDOUT
from mo_imports import delay_import

from mo_logs import logger
from mo_logs.log_usingPrint import StructuredLogger_usingPrint

STACKTRACE = "\n{trace_text|indent}\n{cause_text}"
MO_LOGS_EXTRAS = "mo-logs-extras"
startup_read_settings = delay_import("mo_logs.startup.read_settings")


class BackupLogContext:
    """
    MOSTLY USED FOR TESTING, TO TEMPORARILY CHANGE LOGGING SETTINGS
    """

    def __init__(self, new_settings):
        self.new_settings = new_settings
        self.old_settings = Data(
            trace=logger.trace,
            main_log=logger.main_log,
            logging_multi=logger.logging_multi,
            profiler=logger.profiler,
            error_mode=logger.error_mode,
            extra=logger.extra,
            static_template=logger.static_template,
        )
        self.inside = False

    def __enter__(self):
        if self.inside:
            return
        self.inside = True
        logger._start(settings=self.new_settings)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.inside = False
        logger.stop()
        logger.trace = self.old_settings.trace
        logger.main_log = self.old_settings.main_log
        logger.logging_multi = self.old_settings.logging_multi
        logger.profiler = self.old_settings.profiler
        logger.error_mode = self.old_settings.error_mode
        logger.extra = self.old_settings.extra
        logger.static_template = self.old_settings.static_template


def getLogger(*args, **kwargs):
    return logger


class ExtrasContext:
    def __init__(self, extra):
        self.extra = extra

    def __enter__(self):
        stack = getattr(current_thread(), MO_LOGS_EXTRAS, None)
        if stack:
            stack.append({**stack[-1], **self.extra})
        else:
            stack = [{}, self.extra]
            setattr(current_thread(), MO_LOGS_EXTRAS, stack)

    def __exit__(self, exc_type, exc_val, exc_tb):
        stack = getattr(current_thread(), MO_LOGS_EXTRAS)
        stack.pop()


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
    return _add_thread(StructuredLogger_usingPrint())


def _using_mozlog(config):
    from mo_logs.log_usingMozLog import StructuredLogger_usingMozLog

    return StructuredLogger_usingMozLog(STDOUT, coalesce(config.app_name, config.appname))


def _using_stream(config):
    from mo_logs.log_usingStream import StructuredLogger_usingStream

    return _add_thread(StructuredLogger_usingStream(config.stream))


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


def _add_thread(logger):
    try:
        from mo_logs.log_usingThread import StructuredLogger_usingThread

        return StructuredLogger_usingThread(logger)
    except:
        return logger


def add_param(parsed_template):
    return "".join(f"{text}{{params.{code}}}" if code else text for text, code in parsed_template)
