# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import time

from mo_future import allocate_lock

from mo_logs import logger
from mo_logs.log_usingNothing import StructuredLogger
from mo_logs.strings import expand_template


class StructuredLogger_usingFile(StructuredLogger):
    def __init__(self, file):
        assert file
        from mo_files import File

        self.file = File(file)
        if self.file.exists:
            self.file.backup()
            self.file.delete()

        self.file_lock = allocate_lock()

    def write(self, template, params):
        try:
            with self.file_lock:
                self.file.append(expand_template(template, params))
        except Exception as e:
            logger.warning(
                "Problem writing to file {file}, waiting...", file=self.file.name, cause=e,
            )
            time.sleep(5)
