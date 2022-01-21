# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#


from __future__ import absolute_import, division, unicode_literals

import logging

from mo_dots import unwrap, dict_to_data
from mo_kwargs import override

from mo_logs import logger
from mo_logs.exceptions import FATAL, ERROR, WARNING, ALARM, UNEXPECTED, INFO, NOTE
from mo_logs.log_usingNothing import StructuredLogger
from mo_logs.strings import expand_template
from mo_imports import delay_import

Log = delay_import("mo_logs.Log")

# WRAP PYTHON CLASSIC logger OBJECTS
class StructuredLogger_usingHandler(StructuredLogger):
    @override("settings")
    def __init__(self, settings):
        dummy = Log.trace  # REMOVE ME
        Log.trace = True  # ENSURE TRACING IS ON SO DETAILS ARE CAPTURED
        self.count = 0
        self.logger = logging.Logger("mo-logs", level=logging.INFO)
        self.logger.addHandler(make_handler_from_settings(settings))

    def write(self, template, params):
        record = logging.LogRecord(
            name="mo-logs",
            level=_context_to_level[params.context],
            pathname=params.location.file,
            lineno=params.location.line,
            msg=expand_template(template, params),
            args=params.params,
            exc_info=None,
            func=params.location.method,
            sinfo=params.trace,
            thread=params.thread.id,
            threadName= params.thread.name,
            process=params.machine.pid,
        )
        d=record.__dict__
        for k, v in params.params.leaves():
            d[k] = v
        self.logger.handle(record)
        self.count += 1

    def stop(self):
        # self.logger.shutdown()
        pass


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
    except Exception as e:
        logger.error("Can not find class {{class}}", {"class": path}, cause=e)

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
    params = unwrap(settings)
    try:
        log_instance = constructor(**params)
        return log_instance
    except Exception as cause:
        logger.error("problem with making handler", cause=cause)


_context_to_level = {
    FATAL: logging.CRITICAL,
    ERROR: logging.ERROR,
    WARNING: logging.WARNING,
    ALARM: logging.INFO,
    UNEXPECTED: logging.CRITICAL,
    INFO: logging.INFO,
    NOTE: logging.INFO,
}
