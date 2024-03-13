# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import logging
from datetime import timedelta

from mo_dots import from_data, dict_to_data, is_missing
from mo_imports import delay_import
from mo_json import scrub
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
        self.handler = make_handler_from_config(settings)

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

        if params.cause or record.levelno >= logging.WARNING:
            record.exc_text = expand_template(template, params)
        else:
            record.exc_text = record.msg
        for k, v in params.params.leaves():
            if is_missing(v):
                continue
            if v.__class__.__name__ == "Date":
                ms = round(float("0." + v.format("%f")), 3)
                if not ms:
                    ms = ""
                else:
                    ms = ms[1:]
                v = v.format(f"%Y-%m-%dT%H:%M:%S{ms}Z")
            elif isinstance(v, timedelta):
                v = v.total_seconds()
            else:
                v = scrub(v)
            setattr(record, k, v)
        self.handler.handle(record)
        self.count += 1

    def stop(self):
        self.handler.flush()
        self.handler.close()


def make_handler_from_config(config):
    assert config["class"]
    config.self = None

    config = dict_to_data({**config})

    # IMPORT MODULE FOR HANDLER
    path = config["class"].split(".")
    class_name = path[-1]
    path = ".".join(path[:-1])
    constructor = None
    try:
        temp = __import__(path, globals(), locals(), [class_name], 0)
        constructor = object.__getattribute__(temp, class_name)
    except Exception as cause:
        logger.error("Can not find class {class_name} in {path}", class_name=class_name, path=path, cause=cause)

    # IF WE NEED A FILE, MAKE SURE DIRECTORY EXISTS
    if config.filename != None:
        from mo_files import File

        f = File(config.filename)
        if not f.parent.exists:
            f.parent.create()

    config["class"] = None
    config["cls"] = None
    config["log_type"] = None
    config["settings"] = None
    try:
        log_instance = constructor(**{k:from_data(v) for k, v in config.items()})
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
