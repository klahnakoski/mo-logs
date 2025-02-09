# encoding: utf-8
#
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import importlib
import unittest

from mo_dots import Data
from mo_testing.fuzzytestcase import FuzzyTestCase, add_error_reporting

from mo_logs import constants

CONSTANT = True
EXIST = None
DATA_CONSTANT = Data()


@add_error_reporting
class TestConstants(FuzzyTestCase):
    def test_set_import_self_false(self):
        constants.set({"tests": {"test_constants": {"CONSTANT": False}}})
        self.assertEqual(importlib.import_module(__name__).CONSTANT, False, "expecting change")

    def test_set_self_false(self):
        constants.set({"tests": {"test_constants": {"CONSTANT": False}}})
        self.assertEqual(CONSTANT, False, "expecting change")

    def test_set(self):
        constants.set({"mo_logs": {"constants": {"DEBUG": False}}})
        self.assertEqual(constants.DEBUG, False, "expecting change")

        constants.set({"mo_logs": {"constants": {"DEBUG": True}}})
        self.assertEqual(constants.DEBUG, True, "expecting change")

        constants.set({"mo_logs": {"constants": {"DEBUG": 42}}})
        self.assertEqual(constants.DEBUG, 42, "expecting change")

        constants.set({"mo_logs": {"constants": {"DEBUG": "true"}}})
        self.assertEqual(constants.DEBUG, "true", "expecting change")

    def test_set_self_true(self):
        constants.set({"tests": {"test_constants": {"CONSTANT": True}}})
        self.assertEqual(globals()["CONSTANT"], True, "expecting change")

    def test_set_self_number(self):
        constants.set({"tests": {"test_constants": {"CONSTANT": 42}}})
        self.assertEqual(CONSTANT, 42, "expecting change")

    def test_set_self_string(self):
        constants.set({"tests": {"test_constants": {"CONSTANT": "true"}}})
        self.assertEqual(CONSTANT, "true", "expecting change")

    def test_set_impossible(self):
        with self.assertRaises(Exception):
            constants.set({"DEBUG": "true"})

    def test_set_does_not_exist(self):
        with self.assertRaises(Exception):
            constants.set({"tests": {"test_constants": {"NOT_EXIST": True}}})

    def test_set_does_exist(self):
        constants.set({"tests": {"test_constants": {"EXIST": True}}})
        self.assertEqual(EXIST, True, "expecting change")

    def test_module_does_not_exist(self):
        with self.assertRaises(Exception):
            constants.set({"no_exist": {"VALUE": True}})

    def test_data_constant(self):
        constants.set({"tests": {"test_constants": {"DATA_CONSTANT": {"a": 1}}}})
        self.assertEqual(DATA_CONSTANT.a, 1, "expecting change")


if __name__ == "__main__":
    unittest.main()
