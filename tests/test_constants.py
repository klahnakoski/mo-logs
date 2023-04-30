# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from unittest import skip

from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_logs import constants

CONSTANT = True


class TestConstants(FuzzyTestCase):
    def test_set(self):
        constants.set({"mo_logs": {"constants": {"DEBUG": False}}})
        self.assertEqual(constants.DEBUG, False, "expecting change")

        constants.set({"mo_logs": {"constants": {"DEBUG": True}}})
        self.assertEqual(constants.DEBUG, True, "expecting change")

        constants.set({"mo_logs": {"constants": {"DEBUG": 42}}})
        self.assertEqual(constants.DEBUG, 42, "expecting change")

        constants.set({"mo_logs": {"constants": {"DEBUG": "true"}}})
        self.assertEqual(constants.DEBUG, "true", "expecting change")

    @skip("Can not get to pass on command line")
    def test_set_self_false(self):
        constants.set({"tests": {"test_constants": {"CONSTANT": False}}})
        self.assertEqual(CONSTANT, False, "expecting change")

    @skip("Can not get to pass on command line")
    def test_set_self_true(self):
        constants.set({"tests": {"test_constants": {"CONSTANT": True}}})
        self.assertEqual(globals()["CONSTANT"], True, "expecting change")

    @skip("Can not get to pass on command line")
    def test_set_self_number(self):
        constants.set({"tests": {"test_constants": {"CONSTANT": 42}}})
        self.assertEqual(CONSTANT, 42, "expecting change")

    @skip("Can not get to pass on command line")
    def test_set_self_string(self):
        constants.set({"tests": {"test_constants": {"CONSTANT": "true"}}})
        self.assertEqual(CONSTANT, "true", "expecting change")
