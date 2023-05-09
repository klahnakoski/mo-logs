# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import json
import logging

from mo_dots import from_data, dict_to_data
from mo_imports import delay_import
from mo_kwargs import override

from mo_logs import logger, STACKTRACE
from mo_logs.exceptions import FATAL, ERROR, WARNING, ALARM, UNEXPECTED, INFO, NOTE, format_trace
from mo_logs.log_usingNothing import StructuredLogger
from mo_logs.strings import expand_template

Log = delay_import("mo_logs.Log")
NO_ARGS = tuple()


# WRAP PYTHON CLASSIC logger OBJECTS
class StructuredLogger_usingHandler(StructuredLogger):
    @override("settings")
    def __init__(self, settings):
        try:
            Log.trace = True  # ENSURE TRACING IS ON SO DETAILS ARE CAPTURED
        except Exception as cause:
            Log.trace = True
        self.count = 0
        self.handler = make_handler_from_settings(settings)

    def write(self, template, params):
        record = logging.LogRecord(
            name="mo-logs",
            level=_severity_to_level[params.severity],
            pathname=params.location.file,
            lineno=params.location.line,
            msg=expand_template(template.replace(STACKTRACE, ""), params),
            args=NO_ARGS,
            exc_info=None,
            func=params.location.method,
            sinfo=format_trace(params.trace) or None,
        )
        record.thread = params.thread.id
        record.threadName = params.thread.name
        record.process = params.machine.pid

        record.exc_text = expand_template(template, params)
        for k, v in params.params.leaves():
            setattr(record, k, v)
        self.handler.handle(record)
        self.count += 1

    def stop(self):
        self.handler.flush()
        self.handler.close()


def make_handler_from_settings(settings):
    assert settings["class"]
    settings.self = None

    settings = dict_to_data({**settings})

    # IMPORT MODULE FOR HANDLER
    path = settings["class"].split(".")
    class_name = path[-1]
    path = ".".join(path[:-1])
    constructor = None
    try:
        temp = __import__(path, globals(), locals(), [class_name], 0)
        constructor = object.__getattribute__(temp, class_name)
    except Exception as cause:
        logger.error("Can not find class {{class}}", {"class": path}, cause=cause)

    # IF WE NEED A FILE, MAKE SURE DIRECTORY EXISTS
    if settings.filename != None:
        from mo_files import File

        f = File(settings.filename)
        if not f.parent.exists:
            f.parent.create()

    settings["class"] = None
    settings["cls"] = None
    settings["log_type"] = None
    settings["settings"] = None
    params = from_data(settings)
    try:
        log_instance = constructor(**params)
        return log_instance
    except Exception as cause:
        logger.error("problem with making handler", cause=cause)


_severity_to_level = {
    FATAL: logging.CRITICAL,
    ERROR: logging.ERROR,
    WARNING: logging.WARNING,
    ALARM: logging.INFO,
    UNEXPECTED: logging.CRITICAL,
    INFO: logging.INFO,
    NOTE: logging.INFO,
}
