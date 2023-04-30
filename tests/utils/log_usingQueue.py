# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import re

from mo_threads import Queue

from mo_logs.log_usingNothing import StructuredLogger
from mo_logs.strings import CR, expand_template

DATE_PATTERN = r"\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d(?:\.\d+)* - "


class StructuredLogger_usingQueue(StructuredLogger):
    def __init__(self, name=None):
        queue_name = "log messages to queue"
        if name:
            queue_name += " " + name
        self.queue = Queue(queue_name)

    def write(self, template, params):
        self.queue.add(expand_template(template, params))

    def stop(self):
        self.queue.close()

    def pop(self):
        lines = self.queue.pop()
        output = []
        for l in lines.split(CR):
            # REMOVE FIRST PART, THE TIMESTAMP
            # 0123456789012345678901234567890
            # 2019-01-06 19:13:49.937542 -
            prefix = re.match(DATE_PATTERN, l)
            if prefix:
                l = l[len(prefix.group(0)) :]
            if not l.strip():
                continue
            if l.strip().startswith("File"):
                continue
            output.append(l)
        return CR.join(output).strip()
