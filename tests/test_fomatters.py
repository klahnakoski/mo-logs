# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from math import pi

from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_logs.strings import expand_template


class TestFormatters(FuzzyTestCase):
    def test_upper(self):
        test = expand_template("Hello {{name|upper}}", {"name": "world"})
        self.assertEqual(test, "Hello WORLD")

    def test_places(self):
        test = expand_template("pi = {{pi|round(places=3)}}", {"pi": pi})
        self.assertEqual(test, "pi = 3.14")

    def test_round(self):
        expected = [
            "0.0000000003142",
            "0.000000003142",
            "0.00000003142",
            "0.0000003142",
            "0.000003142",
            "0.00003142",
            "0.0003142",
            "0.003142",
            "0.03142",
            "0.3142",
            "3.142",
            "31.42",
            "314.2",
            "3142",
            "31420",
            "314200",
            "3142000",
            "31420000",
            "314200000",
            "3142000000",
            "31420000000",
            "314200000000",
            "3142000000000",
            "31420000000000",
            "314200000000000",
            "3142000000000000",
            "31420000000000000",
            "314200000000000000",
        ]
        start = -10
        for order in range(start, 18):
            value = pi * (10 ** order)
            test = expand_template("{{value|round(places=4)}}", value={"value": value})
            self.assertEqual(test, expected[order - start])
