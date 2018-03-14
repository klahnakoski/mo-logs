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

from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_logs.strings import expand_template


class TestExcept(FuzzyTestCase):

    def test_upper(self):
        test = expand_template("Hello {{name|upper}}", {"name": "world"})
        self.assertEqual(test, "Hello WORLD")
