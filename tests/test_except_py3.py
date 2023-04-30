# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from mo_future import text
from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_logs import logger


class TestExcept(FuzzyTestCase):
    @classmethod
    def setUpClass(cls):
        logger.start({"trace": False})

    def test_cause_captured(self):
        try:
            try:
                exec(
                    'try:\n    print(1/0)\nexcept Exception as e:\n    raise Exception("test") from e',
                    globals(),
                    locals(),
                )
            except Exception as f:
                logger.error("expected", cause=f)
        except Exception as g:
            self.assertIn("division by zero", g)
            self.assertEqual(g.cause.cause.message, text("ZeroDivisionError: division by zero"))
