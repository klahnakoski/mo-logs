# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import, division, unicode_literals

import logging
from unittest import skipIf

from mo_future import StringIO, PY2
from mo_testing.fuzzytestcase import FuzzyTestCase
from mo_threads import Till

from mo_logs import logger as log


class TestLoggers(FuzzyTestCase):
    @skipIf(PY2, "py2 does not have reload")
    def test_logging(self):
        from importlib import reload

        logging.shutdown()
        reload(logging)

        log_stream = StringIO()
        logger = logging.getLogger()
        logging.basicConfig(stream=log_stream, level=logging.INFO)

        log.start(trace=False, settings={"logs": {"log_type": "logger"}})
        log.note("testing")
        while log.main_log.logger.many[0].count < 1:
            Till(seconds=0.1).wait()
        logs = log_stream.getvalue()

        expected = "testing\n"
        self.assertEqual(logs[-len(expected) :], expected)
