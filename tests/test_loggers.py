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
from importlib import reload

from mo_future import StringIO
from mo_testing.fuzzytestcase import FuzzyTestCase
from mo_threads import Till

from mo_logs import Log


class TestLoggers(FuzzyTestCase):
    def test_logging(self):
        logging.shutdown()
        reload(logging)

        log_stream = StringIO()
        logger = logging.getLogger()
        logging.basicConfig(stream=log_stream, level=logging.INFO)

        Log.start(trace=False, settings={"logs": {"log_type": "logger"}})
        Log.note("testing")
        while Log.main_log.logger.many[0].count < 1:
            Till(seconds=0.1).wait()
        log = log_stream.getvalue()

        expected = "testing\n"
        self.assertEqual(log[-len(expected):], expected)
