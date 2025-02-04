# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from mo_logs import logger as _logger

from mo_logs.exceptions import suppress_exception, Except
from mo_logs.log_usingNothing import StructuredLogger


class StructuredLogger_usingMulti(StructuredLogger):
    def __init__(self):
        self.many = []

    def write(self, template, params):
        bad = []
        for m in self.many:
            try:
                m.write(template, params)
            except Exception as e:
                e = Except.wrap(e)
                bad.append(m)
                _logger.warning(
                    "Logger {type|quote} failed! It will be removed.", type=m.__class__.__name__, cause=e,
                )
        with suppress_exception:
            for b in bad:
                self.many.remove(b)

        return self

    def add_log(self, logger):
        if logger == None:
            _logger.warning("Expecting a non-None logger")

        self.many.append(logger)
        return self

    def remove_log(self, logger):
        self.many.remove(logger)
        return self

    def clear_log(self):
        self.many = []

    def stop(self):
        for m in self.many:
            with suppress_exception:
                m.stop()
