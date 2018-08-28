# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import unicode_literals

from unittest import skipIf

from mo_future import PY2, text_type
from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_logs import Log


class TestExcept(FuzzyTestCase):
    @classmethod
    def setUpClass(cls):
        Log.start({"trace": False})

    @skipIf(PY2, "test python 3 only")
    def test_cause_captured(self):
        try:
            try:
                exec(
                    (
                        "try:\n"
                        "    print(1/0)\n"
                        "except Exception as e:\n"
                        "    raise Exception(\"test\") from e"
                    ),
                    globals(),
                    locals()
                )
            except Exception as f:
                Log.error("expected", cause=f)
        except Exception as g:
            self.assertIn("division by zero", g)
            self.assertEqual(g.cause.cause.message, text_type('division by zero'))


